"""Carga y valida la configuración desde variables de entorno / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env si existe


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "si", "sí")


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _get_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [s.strip() for s in raw.split(",") if s.strip()]


@dataclass
class Config:
    api_key: str = field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", ""))
    paper: bool = field(default_factory=lambda: _get_bool("ALPACA_PAPER", True))

    watchlist: list[str] = field(
        default_factory=lambda: _get_list("WATCHLIST", ["BTC/USD", "ETH/USD", "AAPL", "SPY"])
    )
    sma_fast: int = field(default_factory=lambda: _get_int("SMA_FAST", 10))
    sma_slow: int = field(default_factory=lambda: _get_int("SMA_SLOW", 30))

    trade_notional_usd: float = field(default_factory=lambda: _get_float("TRADE_NOTIONAL_USD", 100.0))
    max_open_positions: int = field(default_factory=lambda: _get_int("MAX_OPEN_POSITIONS", 4))

    loop_interval_seconds: int = field(default_factory=lambda: _get_int("LOOP_INTERVAL_SECONDS", 300))

    def validate(self) -> None:
        """Comprueba que la config tiene sentido antes de arrancar."""
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Faltan ALPACA_API_KEY / ALPACA_SECRET_KEY. "
                "Copia .env.example a .env y rellena tus claves de paper trading."
            )
        if self.sma_fast >= self.sma_slow:
            raise ValueError(
                f"SMA_FAST ({self.sma_fast}) debe ser menor que SMA_SLOW ({self.sma_slow})."
            )
        if self.trade_notional_usd <= 0:
            raise ValueError("TRADE_NOTIONAL_USD debe ser mayor que 0.")
        if self.max_open_positions < 1:
            raise ValueError("MAX_OPEN_POSITIONS debe ser al menos 1.")

    @property
    def mode_label(self) -> str:
        return "PAPER (demo)" if self.paper else "LIVE (dinero REAL)"
