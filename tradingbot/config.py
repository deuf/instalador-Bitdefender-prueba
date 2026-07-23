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
    # Broker de EJECUCIÓN: "etoro" o "alpaca"
    broker: str = field(default_factory=lambda: os.getenv("BROKER", "etoro").strip().lower())
    # Fuente de DATOS: "yfinance" (sin claves), "alpaca" o "etoro".
    # Vacío = se elige solo (yfinance si ejecutas en eToro; alpaca si en Alpaca).
    data_source: str = field(default_factory=lambda: os.getenv("DATA_SOURCE", "").strip().lower())

    # --- Alpaca (ejecución y/o datos de mercado) ---
    api_key: str = field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", ""))
    paper: bool = field(default_factory=lambda: _get_bool("ALPACA_PAPER", True))

    # --- eToro (ejecución) ---
    etoro_api_key: str = field(default_factory=lambda: os.getenv("ETORO_API_KEY", ""))
    etoro_user_key: str = field(default_factory=lambda: os.getenv("ETORO_USER_KEY", ""))
    etoro_demo: bool = field(default_factory=lambda: _get_bool("ETORO_DEMO", True))
    # Mapa "TSLA:1001,BTC/USD:100000" (los instrumentId los ves en tu portal eToro)
    etoro_instruments: str = field(default_factory=lambda: os.getenv("ETORO_INSTRUMENTS", ""))

    watchlist: list[str] = field(
        default_factory=lambda: _get_list("WATCHLIST", ["BTC/USD", "ETH/USD", "AAPL", "SPY"])
    )
    sma_fast: int = field(default_factory=lambda: _get_int("SMA_FAST", 10))
    sma_slow: int = field(default_factory=lambda: _get_int("SMA_SLOW", 30))

    # Estrategia: "sma" (tendencia, velas diarias) o "intraday" (RSI, velas de minutos)
    strategy: str = field(default_factory=lambda: os.getenv("STRATEGY", "sma").strip().lower())
    intraday_minutes: int = field(default_factory=lambda: _get_int("INTRADAY_MINUTES", 5))
    rsi_period: int = field(default_factory=lambda: _get_int("RSI_PERIOD", 14))
    rsi_oversold: float = field(default_factory=lambda: _get_float("RSI_OVERSOLD", 30.0))
    rsi_overbought: float = field(default_factory=lambda: _get_float("RSI_OVERBOUGHT", 70.0))

    trade_notional_usd: float = field(default_factory=lambda: _get_float("TRADE_NOTIONAL_USD", 100.0))
    max_open_positions: int = field(default_factory=lambda: _get_int("MAX_OPEN_POSITIONS", 4))

    # Gestión de riesgo por operación (solo estrategia intradía)
    risk_pct: float = field(default_factory=lambda: _get_float("RISK_PCT", 1.0))
    sl_atr_mult: float = field(default_factory=lambda: _get_float("SL_ATR_MULT", 1.5))
    tp_atr_mult: float = field(default_factory=lambda: _get_float("TP_ATR_MULT", 2.5))

    loop_interval_seconds: int = field(default_factory=lambda: _get_int("LOOP_INTERVAL_SECONDS", 300))

    # Análisis de noticias con IA (Claude). Requiere ANTHROPIC_API_KEY.
    use_ai_news: bool = field(default_factory=lambda: _get_bool("USE_AI_NEWS", False))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "claude-opus-4-8"))

    def __post_init__(self) -> None:
        # Fuente de datos por defecto: yfinance salvo que ejecutes en Alpaca.
        if not self.data_source:
            self.data_source = "alpaca" if self.broker == "alpaca" else "yfinance"

    def validate(self, require_broker: bool = True) -> None:
        """Comprueba que la config tiene sentido antes de arrancar.

        require_broker=False para herramientas que SOLO usan datos (backtest,
        screener): no exigen las claves del broker de ejecución.
        """
        if self.broker not in ("etoro", "alpaca"):
            raise ValueError(f"BROKER debe ser 'etoro' o 'alpaca', no '{self.broker}'.")
        if self.data_source not in ("yfinance", "alpaca", "etoro"):
            raise ValueError(f"DATA_SOURCE debe ser 'yfinance', 'alpaca' o 'etoro', no '{self.data_source}'.")

        # Claves del broker de EJECUCIÓN elegido (solo si se va a operar).
        if require_broker and self.broker == "etoro":
            if not self.etoro_api_key or not self.etoro_user_key:
                raise ValueError(
                    "BROKER=etoro pero faltan ETORO_API_KEY / ETORO_USER_KEY. "
                    "Solicítalas en https://api-portal.etoro.com y ponlas en tu .env."
                )
            if not self.etoro_instruments:
                raise ValueError(
                    "BROKER=etoro necesita ETORO_INSTRUMENTS (mapa símbolo:instrumentId), "
                    "p.ej. 'TSLA:1001,BTC/USD:100000'. Los IDs los ves en tu portal eToro."
                )

        # Claves de Alpaca SOLO si de verdad usas Alpaca (ejecución o datos).
        needs_alpaca = self.data_source == "alpaca" or (require_broker and self.broker == "alpaca")
        if needs_alpaca and (not self.api_key or not self.secret_key):
            raise ValueError(
                "Estás usando Alpaca (ejecución o datos) pero faltan ALPACA_API_KEY / "
                "ALPACA_SECRET_KEY. Son gratis en alpaca.markets."
            )
        if self.sma_fast >= self.sma_slow:
            raise ValueError(
                f"SMA_FAST ({self.sma_fast}) debe ser menor que SMA_SLOW ({self.sma_slow})."
            )
        if self.strategy not in ("sma", "intraday"):
            raise ValueError(f"STRATEGY debe ser 'sma' o 'intraday', no '{self.strategy}'.")
        if not 0 < self.risk_pct <= 100:
            raise ValueError("RISK_PCT debe estar entre 0 y 100.")
        if self.trade_notional_usd <= 0:
            raise ValueError("TRADE_NOTIONAL_USD debe ser mayor que 0.")
        if self.max_open_positions < 1:
            raise ValueError("MAX_OPEN_POSITIONS debe ser al menos 1.")

    @property
    def mode_label(self) -> str:
        if self.broker == "etoro":
            return "eToro DEMO (virtual)" if self.etoro_demo else "eToro REAL (dinero REAL)"
        return "Alpaca PAPER (demo)" if self.paper else "Alpaca LIVE (dinero REAL)"

    @property
    def is_real_money(self) -> bool:
        return (self.broker == "etoro" and not self.etoro_demo) or (
            self.broker == "alpaca" and not self.paper
        )
