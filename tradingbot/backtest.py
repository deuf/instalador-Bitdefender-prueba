"""Backtest de las estrategias sobre datos históricos.

Dos motores:
  - SMA (velas diarias): compra/vende en el cruce de medias.
  - Intradía (velas de minutos): RSI + stop-loss/take-profit por ATR y
    dimensionado por % de riesgo. Simula la salida por SL/TP dentro de la vela.

Sirve para estimar si la estrategia tuvo VENTAJA en el pasado ANTES de arriesgar.
No incluye comisiones ni slippage: los resultados reales serán peores.

Uso:
    python -m tradingbot.backtest AAPL                       # usa STRATEGY del .env
    python -m tradingbot.backtest BTC/USD --strategy sma
    python -m tradingbot.backtest TSLA --strategy intraday --minutes 5 --capital 1000
"""

from __future__ import annotations

import argparse

import pandas as pd

from .config import Config
from .data import MarketData, minute_timeframe
from .metrics import max_drawdown_pct, summarize_trades
from .risk import position_notional, stop_take_levels
from .strategy import Signal, average_true_range, intraday_signal


def backtest_sma(closes: pd.Series, fast: int, slow: int, capital: float) -> dict:
    sma_fast = closes.rolling(fast).mean()
    sma_slow = closes.rolling(slow).mean()
    cash, units, pnls, entry = capital, 0.0, [], 0.0

    for i in range(slow, len(closes)):
        price = closes.iloc[i]
        up = sma_fast.iloc[i - 1] <= sma_slow.iloc[i - 1] and sma_fast.iloc[i] > sma_slow.iloc[i]
        down = sma_fast.iloc[i - 1] >= sma_slow.iloc[i - 1] and sma_fast.iloc[i] < sma_slow.iloc[i]
        if up and units == 0.0:
            units, entry, cash = cash / price, price, 0.0
        elif down and units > 0.0:
            pnls.append(units * (price - entry))
            cash, units = units * price, 0.0

    final = cash + units * closes.iloc[-1]
    result = summarize_trades(pnls, capital, final)
    result["buy_hold_%"] = round((closes.iloc[-1] / closes.iloc[slow] - 1) * 100, 2)
    return result


def backtest_intraday(bars: pd.DataFrame, cfg: Config, capital: float) -> dict:
    """Simula la estrategia intradía con SL/TP y sizing por riesgo."""
    closes, highs, lows = bars["close"], bars["high"], bars["low"]
    equity = capital
    pos: dict | None = None
    pnls: list[float] = []
    equity_curve = [capital]
    start = cfg.rsi_period + 2

    for i in range(start, len(bars)):
        window = bars.iloc[: i + 1]
        signal = intraday_signal(closes.iloc[: i + 1], cfg.rsi_period, cfg.rsi_oversold, cfg.rsi_overbought)
        price, high, low = closes.iloc[i], highs.iloc[i], lows.iloc[i]

        if pos is not None:
            # Salida: conservador -> comprueba stop-loss antes que take-profit.
            exit_price = None
            if low <= pos["sl"]:
                exit_price = pos["sl"]
            elif high >= pos["tp"]:
                exit_price = pos["tp"]
            elif signal is Signal.SELL:
                exit_price = price
            if exit_price is not None:
                pnl = pos["units"] * (exit_price - pos["entry"])
                equity += pnl
                pnls.append(pnl)
                equity_curve.append(equity)
                pos = None

        if pos is None and signal is Signal.BUY:
            atr = average_true_range(window, cfg.rsi_period)
            if atr <= 0:
                continue
            lv = stop_take_levels(price, atr, "buy", cfg.sl_atr_mult, cfg.tp_atr_mult)
            notional = position_notional(equity, cfg.risk_pct, price, lv.stop_loss, max_notional=equity)
            pos = {"entry": price, "sl": lv.stop_loss, "tp": lv.take_profit, "units": notional / price}

    if pos is not None:  # liquida lo que quede abierto al final
        equity += pos["units"] * (closes.iloc[-1] - pos["entry"])
        equity_curve.append(equity)

    result = summarize_trades(pnls, capital, equity)
    result["max_drawdown_%"] = max_drawdown_pct(equity_curve)
    result["buy_hold_%"] = round((closes.iloc[-1] / closes.iloc[start] - 1) * 100, 2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest de estrategias")
    parser.add_argument("symbol", help="símbolo, p.ej. BTC/USD o AAPL")
    parser.add_argument("--strategy", choices=["sma", "intraday"], default=None)
    parser.add_argument("--minutes", type=int, default=None, help="tamaño de vela intradía")
    parser.add_argument("--capital", type=float, default=1000.0)
    parser.add_argument("--limit", type=int, default=None, help="nº de velas a descargar")
    args = parser.parse_args()

    cfg = Config()
    cfg.validate()
    strategy = args.strategy or cfg.strategy
    if args.minutes:
        cfg.intraday_minutes = args.minutes

    data = MarketData(cfg.api_key, cfg.secret_key)

    if strategy == "intraday":
        limit = args.limit or 1000
        bars = data.get_bars(args.symbol, limit=limit, timeframe=minute_timeframe(cfg.intraday_minutes))
        if len(bars) < cfg.rsi_period + 5:
            raise SystemExit(f"Datos insuficientes para {args.symbol} ({len(bars)} velas).")
        result = backtest_intraday(bars, cfg, args.capital)
        header = f"INTRADÍA RSI({cfg.rsi_period}) velas {cfg.intraday_minutes}m | riesgo {cfg.risk_pct}%"
    else:
        limit = args.limit or 365
        closes = data.get_closes(args.symbol, limit=limit)
        if len(closes) < cfg.sma_slow + 1:
            raise SystemExit(f"Datos insuficientes para {args.symbol} ({len(closes)} velas).")
        result = backtest_sma(closes, cfg.sma_fast, cfg.sma_slow, args.capital)
        header = f"SMA {cfg.sma_fast}/{cfg.sma_slow}"

    print(f"\nBacktest {args.symbol}  |  {header}  |  capital inicial {args.capital:.2f}")
    print("-" * 60)
    for k, v in result.items():
        print(f"  {k:<24} {v}")
    print("-" * 60)
    verdict = "MEJOR" if result["retorno_%"] > result["buy_hold_%"] else "PEOR"
    print(f"  La estrategia lo hizo {verdict} que comprar y mantener.")
    pf = result["profit_factor"]
    if isinstance(pf, float) and pf != float("inf"):
        print(f"  Profit factor {pf}: {'rentable (>1)' if pf > 1 else 'PIERDE dinero (<1)'}.")
    print("  Aviso: sin comisiones ni slippage. El pasado no garantiza el futuro.\n")


if __name__ == "__main__":
    main()
