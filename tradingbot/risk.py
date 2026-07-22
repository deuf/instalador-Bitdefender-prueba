"""Gestión de riesgo: stop-loss, take-profit y tamaño de posición.

La gestión de riesgo es lo que separa operar de apostar. Reglas incluidas:
- Nunca arriesgar más de un % pequeño del capital por operación.
- Todo trade lleva stop-loss (dónde admites que te equivocaste) y take-profit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLevels:
    entry: float
    stop_loss: float
    take_profit: float


def stop_take_levels(
    entry: float,
    atr: float,
    side: str = "buy",
    sl_atr_mult: float = 1.5,
    tp_atr_mult: float = 2.5,
) -> RiskLevels:
    """Calcula SL y TP a partir del ATR (volatilidad reciente en precio).

    Usar ATR adapta las distancias a lo que se mueve el activo: stops más
    amplios en activos volátiles, más ceñidos en tranquilos. Con tp>sl el
    ratio riesgo/beneficio es favorable (aquí ~1.66:1 por defecto).
    """
    if entry <= 0 or atr <= 0:
        raise ValueError("entry y atr deben ser positivos.")

    if side.lower() == "buy":
        sl = entry - sl_atr_mult * atr
        tp = entry + tp_atr_mult * atr
    else:  # posición corta
        sl = entry + sl_atr_mult * atr
        tp = entry - tp_atr_mult * atr
    return RiskLevels(entry=entry, stop_loss=round(sl, 4), take_profit=round(tp, 4))


def position_notional(
    equity: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
    max_notional: float | None = None,
) -> float:
    """Importe (USD) a invertir para arriesgar solo `risk_pct`% del capital.

    Si el stop está al X% del precio y quieres arriesgar R dólares, el importe
    de la posición es R / (X%). Así una operación que salta el stop pierde
    exactamente el riesgo previsto, sea cual sea la volatilidad del activo.
    """
    if not 0 < risk_pct <= 100:
        raise ValueError("risk_pct debe estar entre 0 y 100.")
    risk_dollars = equity * (risk_pct / 100.0)
    stop_distance_pct = abs(entry - stop_loss) / entry
    if stop_distance_pct == 0:
        raise ValueError("El stop-loss no puede ser igual al precio de entrada.")

    notional = risk_dollars / stop_distance_pct
    if max_notional is not None:
        notional = min(notional, max_notional)
    return round(notional, 2)
