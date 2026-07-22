"""Fuente de datos de mercado vía Yahoo Finance (yfinance).

Ventaja: NO requiere claves de ninguna clase. Ideal si ejecutas en eToro y no
quieres depender de Alpaca ni para los datos.

Interfaz común de fuentes de datos:
    get_closes(symbol, limit, interval_minutes=None) -> pd.Series
    get_bars(symbol, limit, interval_minutes=None)   -> pd.DataFrame(OHLCV)
donde interval_minutes=None significa velas diarias.
"""

from __future__ import annotations

import pandas as pd

from .symbols import to_yfinance


class YFinanceData:
    def __init__(self) -> None:
        try:
            import yfinance  # noqa: F401  (comprobación temprana)
        except ImportError as exc:
            raise ImportError(
                "Falta 'yfinance'. Instálalo con: pip install yfinance"
            ) from exc

    @staticmethod
    def _period_interval(limit: int, interval_minutes: int | None) -> tuple[str, str]:
        """Elige period/interval de yfinance según lo pedido.

        yfinance limita el histórico intradía (p.ej. velas de minutos solo de
        los últimos ~60 días), así que ajustamos el período en consecuencia.
        """
        if interval_minutes:
            interval = f"{interval_minutes}m"
            period = "60d" if interval_minutes >= 2 else "7d"
        else:
            interval = "1d"
            # margen amplio para tener suficientes velas diarias
            period = "2y" if limit > 250 else "1y"
        return period, interval

    def get_bars(self, symbol: str, limit: int = 60, interval_minutes: int | None = None) -> pd.DataFrame:
        import yfinance as yf

        period, interval = self._period_interval(limit, interval_minutes)
        df = yf.download(
            to_yfinance(symbol), period=period, interval=interval,
            progress=False, auto_adjust=True,
        )
        if df is None or df.empty:
            return pd.DataFrame()

        # yfinance puede devolver columnas MultiIndex (ticker, campo); aplanamos.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]

        cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
        return df[cols].astype("float64").tail(limit)

    def get_closes(self, symbol: str, limit: int = 200, interval_minutes: int | None = None) -> pd.Series:
        bars = self.get_bars(symbol, limit=limit, interval_minutes=interval_minutes)
        if bars.empty or "close" not in bars.columns:
            return pd.Series(dtype="float64")
        return bars["close"]
