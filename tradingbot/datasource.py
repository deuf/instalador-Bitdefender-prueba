"""Selector de fuente de datos de mercado (imports perezosos).

Devuelve un objeto con la interfaz común:
    get_closes(symbol, limit, interval_minutes=None)
    get_bars(symbol, limit, interval_minutes=None)

Fuentes:
    - "yfinance": Yahoo Finance, SIN claves (por defecto si ejecutas en eToro).
    - "alpaca":   Alpaca, requiere alpaca-py y claves gratuitas.
    - "etoro":    feed nativo de eToro (requiere la ruta de velas de tu portal).
"""

from __future__ import annotations


def make_data_source(cfg):
    source = cfg.data_source
    if source == "yfinance":
        from .data_yf import YFinanceData
        return YFinanceData()
    if source == "alpaca":
        from .data import MarketData
        return MarketData(cfg.api_key, cfg.secret_key)
    if source == "etoro":
        from .data_etoro import EToroData
        return EToroData(cfg.etoro_api_key, cfg.etoro_user_key, demo=cfg.etoro_demo,
                         instruments_raw=cfg.etoro_instruments)
    raise ValueError(f"DATA_SOURCE desconocido: '{source}' (usa yfinance, alpaca o etoro).")
