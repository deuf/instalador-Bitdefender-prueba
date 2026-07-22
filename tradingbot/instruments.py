"""Mapa símbolo <-> instrumentId de eToro.

eToro identifica cada activo con un número (instrumentId), no con el ticker.
Por ejemplo, "TSLA" puede ser 1001. Estos IDs se consultan en el portal de eToro
(endpoint de instrumentos) y se configuran en ETORO_INSTRUMENTS del .env con el
formato:  "TSLA:1001,NVDA:1002,BTC/USD:100000"
"""

from __future__ import annotations


def parse_instruments(raw: str) -> dict[str, int]:
    """Convierte 'TSLA:1001,BTC/USD:100000' en {'TSLA': 1001, 'BTC/USD': 100000}."""
    mapping: dict[str, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"Entrada inválida en ETORO_INSTRUMENTS: '{pair}' (falta ':').")
        symbol, _, id_str = pair.rpartition(":")
        symbol = symbol.strip()
        try:
            mapping[symbol] = int(id_str.strip())
        except ValueError as exc:
            raise ValueError(f"instrumentId no numérico en '{pair}'.") from exc
    return mapping


class Instruments:
    """Búsqueda en ambos sentidos entre ticker e instrumentId."""

    def __init__(self, raw: str) -> None:
        self._forward = parse_instruments(raw)
        self._reverse = {v: k for k, v in self._forward.items()}

    def id_for(self, symbol: str) -> int:
        if symbol not in self._forward:
            raise KeyError(
                f"No hay instrumentId para '{symbol}'. Añádelo a ETORO_INSTRUMENTS."
            )
        return self._forward[symbol]

    def symbol_for(self, instrument_id: int) -> str | None:
        return self._reverse.get(int(instrument_id))

    def symbols(self) -> list[str]:
        return list(self._forward.keys())
