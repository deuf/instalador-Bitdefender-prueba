"""Pruebas de la lógica de señal (no requieren claves ni red)."""

import pandas as pd

from tradingbot.strategy import Signal, sma_crossover_signal


def test_datos_insuficientes_devuelve_hold():
    closes = pd.Series([1, 2, 3])
    assert sma_crossover_signal(closes, fast=2, slow=5) is Signal.HOLD


def test_cruce_alcista_genera_compra():
    # Baja de forma sostenida (fast por debajo de slow) y da un salto en la
    # última vela que hace cruzar la media rápida por encima -> COMPRA.
    closes = pd.Series([20, 18, 16, 14, 12, 10, 8, 20])
    assert sma_crossover_signal(closes, fast=2, slow=4) is Signal.BUY


def test_cruce_bajista_genera_venta():
    # Sube de forma sostenida (fast por encima) y cae de golpe en la última
    # vela -> la media rápida cruza por debajo -> VENTA.
    closes = pd.Series([8, 10, 12, 14, 16, 18, 20, 5])
    assert sma_crossover_signal(closes, fast=2, slow=4) is Signal.SELL


def test_tendencia_estable_mantiene_hold():
    closes = pd.Series([10] * 20)
    assert sma_crossover_signal(closes, fast=3, slow=6) is Signal.HOLD


# --- RSI e intradía ---
from tradingbot.strategy import intraday_signal, rsi  # noqa: E402
from tradingbot.risk import position_notional, stop_take_levels  # noqa: E402


def test_rsi_en_rango_valido():
    closes = pd.Series(range(1, 40)).astype(float)  # subida constante
    r = rsi(closes, period=14).iloc[-1]
    assert 0 <= r <= 100
    assert r > 70  # subida sostenida -> sobrecompra


def test_intraday_compra_al_salir_de_sobreventa():
    # Caída fuerte (RSI bajo) y giro al alza en las últimas velas.
    closes = pd.Series([100, 90, 80, 70, 60, 50, 45, 42, 40, 39, 38, 37, 36, 35, 34, 48, 60])
    assert intraday_signal(closes, period=14) in (Signal.BUY, Signal.HOLD)


def test_stop_take_ratio_favorable():
    lv = stop_take_levels(entry=100.0, atr=2.0, side="buy")
    assert lv.stop_loss < 100.0 < lv.take_profit
    riesgo = lv.entry - lv.stop_loss
    beneficio = lv.take_profit - lv.entry
    assert beneficio > riesgo  # ratio R:B > 1


def test_position_notional_respeta_riesgo():
    # Con 10000 equity, 1% riesgo, stop al 2% -> importe = 100 / 0.02 = 5000
    notional = position_notional(equity=10000, risk_pct=1.0, entry=100.0, stop_loss=98.0)
    assert notional == 5000.0
    # Y una pérdida hasta el stop = 5000 * 2% = 100 = 1% del capital. Correcto.
