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
