"""Fuente de datos de mercado vía Alpaca (opcional).

Solo se importa si DATA_SOURCE=alpaca. Requiere la librería alpaca-py y claves
gratuitas de Alpaca. Interfaz común de fuentes de datos:
    get_closes(symbol, limit, interval_minutes=None) -> pd.Series
    get_bars(symbol, limit, interval_minutes=None)   -> pd.DataFrame(OHLCV)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from .symbols import is_crypto


def _timeframe(interval_minutes: int | None) -> TimeFrame:
    if interval_minutes:
        return TimeFrame(interval_minutes, TimeFrameUnit.Minute)
    return TimeFrame.Day


class MarketData:
    """Wrapper unificado para pedir velas de acciones/ETF y cripto en Alpaca."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        self._stock = StockHistoricalDataClient(api_key, secret_key)
        self._crypto = CryptoHistoricalDataClient(api_key, secret_key)

    def _fetch(self, symbol: str, limit: int, interval_minutes: int | None) -> pd.DataFrame:
        timeframe = _timeframe(interval_minutes)
        # margen de tiempo generoso para asegurar suficientes velas
        span_days = (limit * max(interval_minutes or 1440, 1)) // (60 * 6) + 10
        start = datetime.now(timezone.utc) - timedelta(days=max(span_days, limit * 2 + 10))

        if is_crypto(symbol):
            request = CryptoBarsRequest(symbol_or_symbols=symbol, timeframe=timeframe, start=start)
            bars = self._crypto.get_crypto_bars(request)
        else:
            request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=timeframe, start=start)
            bars = self._stock.get_stock_bars(request)

        df = bars.df
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level="symbol")
        return df

    def get_bars(self, symbol: str, limit: int = 60, interval_minutes: int | None = None) -> pd.DataFrame:
        df = self._fetch(symbol, limit, interval_minutes)
        if df.empty:
            return pd.DataFrame()
        cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
        return df[cols].astype("float64").tail(limit)

    def get_closes(self, symbol: str, limit: int = 200, interval_minutes: int | None = None) -> pd.Series:
        df = self._fetch(symbol, limit, interval_minutes)
        if df.empty or "close" not in df.columns:
            return pd.Series(dtype="float64")
        return df["close"].astype("float64").tail(limit)
