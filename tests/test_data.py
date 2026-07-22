"""Pruebas de utilidades de símbolos y mapeo de timeframe de yfinance."""

from tradingbot.data_yf import YFinanceData
from tradingbot.symbols import is_crypto, to_yfinance


def test_is_crypto():
    assert is_crypto("BTC/USD")
    assert not is_crypto("AAPL")


def test_to_yfinance_convierte_cripto():
    assert to_yfinance("BTC/USD") == "BTC-USD"
    assert to_yfinance("AAPL") == "AAPL"


def test_period_interval_diario():
    period, interval = YFinanceData._period_interval(100, None)
    assert interval == "1d"
    assert period in ("1y", "2y")


def test_period_interval_intradia():
    period, interval = YFinanceData._period_interval(500, 5)
    assert interval == "5m"
    assert period == "60d"
