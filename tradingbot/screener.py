"""Screener intradía: puntúa activos por su IDONEIDAD para operar intradía.

IMPORTANTE — qué mide y qué NO mide:
Este screener NO predice si una acción subirá. Eso es matemáticamente imposible
de garantizar. Lo que hace es medir las dos condiciones OBJETIVAS que hacen que
un activo sea operable intradía, que es lo único que sí se puede cuantificar:

  1. VOLATILIDAD (rango diario medio, ATR%): sin movimiento no hay beneficio
     intradía posible. Demasiada tampoco es buena (riesgo alto).
  2. LIQUIDEZ (volumen medio en USD): permite entrar y salir sin mover el precio
     y con spreads estrechos.

El "score" es una combinación de ambas: un activo con score alto es más APTO
para intradía. No es una recomendación de compra ni una probabilidad de ganar.

Uso:
    python -m tradingbot.screener
    python -m tradingbot.screener --symbols TSLA,NVDA,AAPL,MARA --days 30
"""

from __future__ import annotations

import argparse

import pandas as pd

from .config import Config
from .data import MarketData


def _atr_pct(bars: pd.DataFrame, period: int = 14) -> float:
    """Average True Range en % del precio: mide el rango diario típico."""
    high, low, close = bars["high"], bars["low"], bars["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = true_range.rolling(period).mean().iloc[-1]
    last_price = close.iloc[-1]
    return float(atr / last_price * 100) if last_price else 0.0


def _avg_dollar_volume(bars: pd.DataFrame) -> float:
    """Volumen medio en dólares = liquidez (más alto = más fácil entrar/salir)."""
    if "volume" not in bars.columns:
        return 0.0
    return float((bars["close"] * bars["volume"]).mean())


def score_symbol(bars: pd.DataFrame) -> dict:
    if len(bars) < 15:
        return {}
    atr = _atr_pct(bars)
    dollar_vol = _avg_dollar_volume(bars)
    last = float(bars["close"].iloc[-1])

    # Idoneidad de volatilidad: penaliza tanto lo demasiado plano como lo extremo.
    # Zona dulce intradía ~ 2%-6% de rango diario.
    if atr < 1.0:
        vol_score = atr / 1.0 * 40          # muy plano: poco margen
    elif atr <= 6.0:
        vol_score = 100 - abs(atr - 4.0) * 8  # zona buena, pico ~4%
    else:
        vol_score = max(0.0, 60 - (atr - 6.0) * 6)  # demasiado errático

    # Liquidez: escala logarítmica; >100M USD/día = plenamente líquido.
    import math
    liq_score = min(100.0, max(0.0, (math.log10(dollar_vol + 1) - 5) / 3 * 100)) if dollar_vol else 0.0

    composite = round(0.5 * vol_score + 0.5 * liq_score, 1)
    return {
        "precio": round(last, 2),
        "ATR_%": round(atr, 2),
        "vol_USD_dia_M": round(dollar_vol / 1e6, 1),
        "aptitud_intradia": composite,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Screener de idoneidad intradía")
    parser.add_argument("--symbols", help="lista separada por comas; por defecto usa la WATCHLIST")
    parser.add_argument("--days", type=int, default=30, help="nº de velas diarias a analizar")
    args = parser.parse_args()

    cfg = Config()
    cfg.validate()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else cfg.watchlist

    data = MarketData(cfg.api_key, cfg.secret_key)
    rows = []
    for sym in symbols:
        try:
            bars = data.get_bars(sym, limit=args.days)
            metrics = score_symbol(bars)
            if metrics:
                rows.append({"símbolo": sym, **metrics})
            else:
                print(f"  (datos insuficientes para {sym})")
        except Exception as exc:
            print(f"  (error con {sym}: {exc})")

    if not rows:
        raise SystemExit("No se pudo puntuar ningún símbolo.")

    df = pd.DataFrame(rows).sort_values("aptitud_intradia", ascending=False)
    print("\n" + "=" * 60)
    print("RANKING DE IDONEIDAD INTRADÍA (mayor score = más operable)")
    print("=" * 60)
    print(df.to_string(index=False))
    print("\nRecuerda: score alto = líquido y con movimiento, NO = 'va a subir'.")
    print("El screener elige el TERRENO; la estrategia y tu gestión de riesgo deciden el resultado.\n")


if __name__ == "__main__":
    main()
