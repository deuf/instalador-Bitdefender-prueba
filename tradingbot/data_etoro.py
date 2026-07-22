"""Fuente de datos de mercado vía el feed NATIVO de eToro.

Permite operar 100% con eToro (datos + ejecución), sin Alpaca ni Yahoo.

⚠️ La ruta exacta de velas/precios de eToro está en su documentación tras login.
Se centraliza en ENDPOINT_CANDLES para que la ajustes con lo que veas en tu
portal (https://api-portal.etoro.com). Mientras no la confirmes, esta fuente
lanzará un error claro en lugar de devolver datos incorrectos.

Interfaz común:
    get_closes(symbol, limit, interval_minutes=None) -> pd.Series
    get_bars(symbol, limit, interval_minutes=None)   -> pd.DataFrame(OHLCV)
"""

from __future__ import annotations

import pandas as pd
import requests

from .instruments import Instruments

BASE_URL = "https://public-api.etoro.com"
# ⚠️ VERIFICAR/AJUSTAR con la ruta real de velas de tu portal eToro:
ENDPOINT_CANDLES = "/api/v1/market-data/candles"


class EToroData:
    def __init__(self, api_key: str, user_key: str, demo: bool = True,
                 instruments_raw: str = "", timeout: int = 20) -> None:
        if not api_key or not user_key:
            raise ValueError("DATA_SOURCE=etoro requiere ETORO_API_KEY / ETORO_USER_KEY.")
        self.instruments = Instruments(instruments_raw) if instruments_raw else None
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"x-api-key": api_key, "x-user-key": user_key})

    def _fetch(self, symbol: str, limit: int, interval_minutes: int | None) -> pd.DataFrame:
        if self.instruments is None:
            raise RuntimeError("DATA_SOURCE=etoro necesita ETORO_INSTRUMENTS para mapear el símbolo.")
        instrument_id = self.instruments.id_for(symbol)
        interval = f"{interval_minutes}min" if interval_minutes else "1day"
        params = {"instrumentId": instrument_id, "interval": interval, "limit": limit}

        try:
            resp = self._session.get(BASE_URL + ENDPOINT_CANDLES, params=params, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            raise RuntimeError(
                "No se pudieron obtener velas de eToro. Verifica ENDPOINT_CANDLES y el "
                f"formato de parámetros en tu portal. Detalle: {exc}"
            ) from exc

        candles = payload.get("candles", payload) if isinstance(payload, dict) else payload
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles)
        # Normaliza nombres habituales (open/high/low/close) tolerando variantes.
        rename = {c: c.lower() for c in df.columns}
        df = df.rename(columns=rename)
        return df

    def get_bars(self, symbol: str, limit: int = 60, interval_minutes: int | None = None) -> pd.DataFrame:
        df = self._fetch(symbol, limit, interval_minutes)
        cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
        return df[cols].astype("float64").tail(limit) if cols else pd.DataFrame()

    def get_closes(self, symbol: str, limit: int = 200, interval_minutes: int | None = None) -> pd.Series:
        bars = self.get_bars(symbol, limit=limit, interval_minutes=interval_minutes)
        if bars.empty or "close" not in bars.columns:
            return pd.Series(dtype="float64")
        return bars["close"]
