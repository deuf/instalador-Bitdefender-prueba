"""Pruebas del mapa de instrumentos de eToro (ticker <-> instrumentId)."""

import pytest

from tradingbot.instruments import Instruments, parse_instruments


def test_parse_basico():
    m = parse_instruments("TSLA:1001,NVDA:1002")
    assert m == {"TSLA": 1001, "NVDA": 1002}


def test_parse_cripto_con_barra():
    # El símbolo lleva ':' final para el id, pero el ticker tiene '/'.
    m = parse_instruments("BTC/USD:100000")
    assert m == {"BTC/USD": 100000}


def test_parse_ignora_espacios_y_vacios():
    m = parse_instruments(" TSLA:1001 , , NVDA:1002 ")
    assert m == {"TSLA": 1001, "NVDA": 1002}


def test_parse_id_no_numerico_falla():
    with pytest.raises(ValueError):
        parse_instruments("TSLA:abc")


def test_lookup_bidireccional():
    inst = Instruments("TSLA:1001,BTC/USD:100000")
    assert inst.id_for("TSLA") == 1001
    assert inst.symbol_for(100000) == "BTC/USD"
    assert inst.symbols() == ["TSLA", "BTC/USD"]


def test_simbolo_desconocido_lanza():
    inst = Instruments("TSLA:1001")
    with pytest.raises(KeyError):
        inst.id_for("AAPL")
