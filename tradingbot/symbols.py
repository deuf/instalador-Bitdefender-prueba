"""Utilidades de símbolos, sin dependencias externas (no importa Alpaca).

Se separa aquí para que módulos como el broker o las fuentes de datos puedan
usar estas funciones sin arrastrar la librería de Alpaca.
"""

from __future__ import annotations


def is_crypto(symbol: str) -> bool:
    """Los símbolos de cripto llevan barra: 'BTC/USD'."""
    return "/" in symbol


def to_yfinance(symbol: str) -> str:
    """Convierte el símbolo al formato de Yahoo Finance ('BTC/USD' -> 'BTC-USD')."""
    return symbol.replace("/", "-") if is_crypto(symbol) else symbol
