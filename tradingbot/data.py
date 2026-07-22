"""Descarga de datos históricos de precios (acciones/ETF y cripto) vía Alpaca."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit


def is_crypto(symbol: str) -> bool:
    """Los símbolos de cripto en Alpaca llevan barra: 'BTC/USD'."""
    return "/" in symbol


def minute_timeframe(minutes: int) -> TimeFrame:
    """Construye un TimeFrame de N minutos para datos intradía."""
    return TimeFrame(minutes, TimeFrameUnit.Minute)


class MarketData:
    """Wrapper unificado para pedir velas de acciones/ETF y cripto."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        # El cliente de cripto no exige claves, pero las pasamos por consistencia.
        self._stock = StockHistoricalDataClient(api_key, secret_key)
        self._crypto = CryptoHistoricalDataClient(api_key, secret_key)

    def get_closes(self, symbol: str, limit: int = 200, timeframe: TimeFrame | None = None) -> pd.Series:
        """Devuelve una serie de precios de cierre indexada por tiempo.

        Pide un margen amplio de días para asegurar suficientes velas.
        """
        timeframe = timeframe or TimeFrame.Day
        start = datetime.now(timezone.utc) - timedelta(days=limit * 2 + 10)

        if is_crypto(symbol):
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol, timeframe=timeframe, start=start
            )
            bars = self._crypto.get_crypto_bars(request)
        else:
            request = StockBarsRequest(
                symbol_or_symbols=symbol, timeframe=timeframe, start=start
            )
            bars = self._stock.get_stock_bars(request)

        df = bars.df
        if df is None or df.empty:
            return pd.Series(dtype="float64")

        # Cuando se pide un solo símbolo el índice es MultiIndex (symbol, timestamp).
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level="symbol")

        return df["close"].astype("float64").tail(limit)

    def get_bars(self, symbol: str, limit: int = 60, timeframe: TimeFrame | None = None) -> pd.DataFrame:
        """Devuelve un DataFrame con open/high/low/close/volume."""
        timeframe = timeframe or TimeFrame.Day
        start = datetime.now(timezone.utc) - timedelta(days=limit * 2 + 10)

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
        cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
        return df[cols].astype("float64").tail(limit)
