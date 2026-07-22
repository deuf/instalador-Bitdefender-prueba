"""Pruebas de métricas y del motor de backtest intradía (sin red ni claves)."""

import pandas as pd

from tradingbot.metrics import max_drawdown_pct, summarize_trades


def test_max_drawdown_calcula_peor_caida():
    # Sube a 120, cae a 90 (-25% desde el pico), recupera.
    curve = [100, 110, 120, 105, 90, 100]
    assert max_drawdown_pct(curve) == -25.0


def test_max_drawdown_sin_caida_es_cero():
    assert max_drawdown_pct([100, 110, 120, 130]) == 0.0


def test_summarize_trades_metricas_basicas():
    pnls = [100, -50, 200, -50]  # 2 ganan, 2 pierden; gana 300, pierde 100
    res = summarize_trades(pnls, capital=1000, final_equity=1200)
    assert res["operaciones"] == 4
    assert res["aciertos"] == 2
    assert res["win_rate_%"] == 50.0
    assert res["profit_factor"] == 3.0      # 300 / 100
    assert res["retorno_%"] == 20.0         # 1200 / 1000


def test_summarize_sin_operaciones_no_rompe():
    res = summarize_trades([], capital=1000, final_equity=1000)
    assert res["operaciones"] == 0
    assert res["win_rate_%"] == 0.0
