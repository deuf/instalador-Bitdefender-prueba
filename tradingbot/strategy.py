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


def rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (0-100). Wilder smoothing."""
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    result = 100 - 100 / (1 + rs)
    # Casos límite: solo ganancias -> 100 (sobrecompra máxima); sin
    # movimiento -> 50 (neutral). Evita el NaN de dividir por cero.
    result = result.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    result = result.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return result


def intraday_signal(
    closes: pd.Series,
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> Signal:
    """Estrategia intradía de reversión a la media con RSI.

    Pensada para velas de minutos (5m/15m):
    - COMPRA cuando el RSI SALE de sobreventa (cruza el nivel `oversold` al alza).
    - VENTA/cierre cuando el RSI SALE de sobrecompra (cruza `overbought` a la baja).

    Operar en el cruce (y no solo por estar por debajo/encima) evita entrar
    demasiado pronto en una caída que sigue.
    """
    if len(closes) < period + 2:
        return Signal.HOLD

    r = rsi(closes, period)
    now, prev = r.iloc[-1], r.iloc[-2]

    if prev <= oversold and now > oversold:
        return Signal.BUY
    if prev >= overbought and now < overbought:
        return Signal.SELL
    return Signal.HOLD
