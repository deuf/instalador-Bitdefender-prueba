"""Estrategia de trading: cruce de medias móviles simples (SMA crossover).

Es una estrategia clásica y fácil de entender, pensada como PUNTO DE PARTIDA:
- Señal de COMPRA cuando la media rápida cruza por ENCIMA de la lenta.
- Señal de VENTA cuando la media rápida cruza por DEBAJO de la lenta.

No es una fórmula mágica de ganancias: sirve como base para que la valides
(con backtest) y la sustituyas por tu propia lógica.
"""

from __future__ import annotations

from enum import Enum

import pandas as pd


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def sma_crossover_signal(closes: pd.Series, fast: int, slow: int) -> Signal:
    """Calcula la señal a partir de la última vela cerrada.

    Detecta el CRUCE comparando la posición relativa de las medias en la
    vela actual frente a la anterior, para no repetir señales cada ciclo.
    """
    if len(closes) < slow + 1:
        return Signal.HOLD  # datos insuficientes

    sma_fast = closes.rolling(fast).mean()
    sma_slow = closes.rolling(slow).mean()

    fast_now, fast_prev = sma_fast.iloc[-1], sma_fast.iloc[-2]
    slow_now, slow_prev = sma_slow.iloc[-1], sma_slow.iloc[-2]

    crossed_up = fast_prev <= slow_prev and fast_now > slow_now
    crossed_down = fast_prev >= slow_prev and fast_now < slow_now

    if crossed_up:
        return Signal.BUY
    if crossed_down:
        return Signal.SELL
    return Signal.HOLD
