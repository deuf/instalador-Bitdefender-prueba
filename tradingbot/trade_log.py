"""Registro de operaciones en CSV para medir si la estrategia tiene ventaja real.

Sin registro no sabes si ganas o pierdes: la memoria engaña. Cada operación se
apila en un CSV que luego puedes analizar (win-rate, resultado acumulado...).
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

FIELDS = ["timestamp", "symbol", "side", "action", "price", "notional_usd", "signal", "mode", "note"]


class TradeLog:
    def __init__(self, path: str = "logs/trades.csv") -> None:
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(FIELDS)

    def record(
        self,
        symbol: str,
        side: str,
        action: str,
        price: float,
        notional_usd: float = 0.0,
        signal: str = "",
        mode: str = "paper",
        note: str = "",
    ) -> None:
        row = [
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            symbol, side, action, round(price, 4), round(notional_usd, 2), signal, mode, note,
        ]
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def summary(self) -> dict:
        """Cuenta operaciones registradas por acción (open/close)."""
        opens = closes = 0
        with open(self.path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["action"] == "open":
                    opens += 1
                elif r["action"] == "close":
                    closes += 1
        return {"aperturas": opens, "cierres": closes, "archivo": self.path}
