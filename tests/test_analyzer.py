"""Pruebas del analizador multifactor (partes sin red)."""

import numpy as np
import pandas as pd

from tradingbot.analyzer import analyze, score_sentiment


def test_sentiment_positivo():
    score, pos, neg = score_sentiment(["Apple beats earnings, stock surges to record high"])
    assert score > 0 and pos > neg


def test_sentiment_negativo():
    score, pos, neg = score_sentiment(["Tesla plunges after analyst downgrade and weak sales"])
    assert score < 0 and neg > pos


def test_sentiment_vacio_es_neutral():
    assert score_sentiment([]) == (0.0, 0, 0)


class _FakeData:
    """Fuente de datos falsa: serie alcista, para probar analyze sin red."""

    def get_bars(self, symbol, limit=300, interval_minutes=None):
        n = 260
        idx = pd.date_range("2025-01-01", periods=n)
        price = np.linspace(100, 200, n)  # tendencia claramente alcista
        return pd.DataFrame(
            {"open": price, "high": price + 1, "low": price - 1, "close": price,
             "volume": [1_000_000] * n},
            index=idx,
        )


def test_analyze_tendencia_alcista_da_estructura(monkeypatch):
    # Evita la llamada de red a noticias.
    import tradingbot.analyzer as az
    monkeypatch.setattr(az, "fetch_news_titles", lambda *a, **k: [])
    r = analyze("TEST", _FakeData())
    assert r["veredicto"] in ("COMPRAR", "MANTENER", "VENDER")
    assert "factores" in r and len(r["factores"]) >= 3
    # En tendencia alcista pura, precio>SMA50 y SMA50>SMA200 -> puntuación positiva
    assert r["puntuacion"] > 0
