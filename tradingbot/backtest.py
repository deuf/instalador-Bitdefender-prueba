"""Backtest sencillo de la estrategia SMA sobre datos históricos.

Simula comprar con TODO el capital en la señal de compra y vender en la de
venta (largo-plano, sin apalancamiento ni comisiones). Sirve para hacerte una
idea rápida de si la estrategia tiene sentido en un activo ANTES de operar.

Uso:
    python -m tradingbot.backtest BTC/USD
    python -m tradingbot.backtest AAPL --fast 10 --slow 30 --capital 1000
"""

from __future__ import annotations

import argparse

import pandas as pd

from .config import Config
from .data import MarketData


def backtest(closes: pd.Series, fast: int, slow: int, capital: float) -> dict:
    sma_fast = closes.rolling(fast).mean()
    sma_slow = closes.rolling(slow).mean()

    cash = capital
    units = 0.0
    trades = 0
    wins = 0
    entry_price = 0.0

    for i in range(slow, len(closes)):
        price = closes.iloc[i]
        fast_now, fast_prev = sma_fast.iloc[i], sma_fast.iloc[i - 1]
        slow_now, slow_prev = sma_slow.iloc[i], sma_slow.iloc[i - 1]

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up and units == 0.0:  # abrir
            units = cash / price
            entry_price = price
            cash = 0.0
        elif crossed_down and units > 0.0:  # cerrar
            cash = units * price
            trades += 1
            if price > entry_price:
                wins += 1
            units = 0.0

    final_value = cash + units * closes.iloc[-1]  # liquida lo que quede abierto
    ret_pct = (final_value / capital - 1) * 100
    buy_hold_pct = (closes.iloc[-1] / closes.iloc[slow] - 1) * 100

    return {
        "velas": len(closes),
        "operaciones": trades,
        "aciertos": wins,
        "win_rate_%": round((wins / trades * 100) if trades else 0.0, 1),
        "valor_final": round(final_value, 2),
        "retorno_estrategia_%": round(ret_pct, 2),
        "retorno_buy_hold_%": round(buy_hold_pct, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest de la estrategia SMA")
    parser.add_argument("symbol", help="símbolo, p.ej. BTC/USD o AAPL")
    parser.add_argument("--fast", type=int, default=None)
    parser.add_argument("--slow", type=int, default=None)
    parser.add_argument("--capital", type=float, default=1000.0)
    parser.add_argument("--limit", type=int, default=365, help="nº de velas a descargar")
    args = parser.parse_args()

    cfg = Config()
    cfg.validate()
    fast = args.fast or cfg.sma_fast
    slow = args.slow or cfg.sma_slow

    data = MarketData(cfg.api_key, cfg.secret_key)
    closes = data.get_closes(args.symbol, limit=args.limit)
    if len(closes) < slow + 1:
        raise SystemExit(f"Datos insuficientes para {args.symbol} ({len(closes)} velas).")

    result = backtest(closes, fast, slow, args.capital)

    print(f"\nBacktest {args.symbol}  |  SMA {fast}/{slow}  |  capital inicial {args.capital:.2f}")
    print("-" * 55)
    for k, v in result.items():
        print(f"  {k:<24} {v}")
    print("-" * 55)
    verdict = "MEJOR" if result["retorno_estrategia_%"] > result["retorno_buy_hold_%"] else "PEOR"
    print(f"  La estrategia lo hizo {verdict} que comprar y mantener.\n")
    print("  Aviso: sin comisiones ni slippage. El pasado no garantiza el futuro.\n")


if __name__ == "__main__":
    main()
