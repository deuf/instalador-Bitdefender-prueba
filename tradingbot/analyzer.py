"""Analizador multifactor: combina técnica + noticias en un veredicto razonado.

Para un símbolo, calcula varias métricas y las combina en una puntuación que
sugiere COMPRAR / MANTENER / VENDER, explicando el porqué de cada factor.

⚠️ IMPORTANTE: es una herramienta de APOYO A LA DECISIÓN, no una predicción.
Combinar señales mejora el fundamento de la decisión, pero NO garantiza acertar.
El sentimiento de noticias aquí es básico (léxico de palabras): para las grandes
instituciones la noticia ya está descontada cuando tú la lees.

Uso:
    python -m tradingbot.analyzer AAPL
    python -m tradingbot.analyzer TSLA NVDA BTC/USD
"""

from __future__ import annotations

import argparse

import pandas as pd

from .config import Config
from .datasource import make_data_source
from .strategy import average_true_range, rsi
from .symbols import to_yfinance

# Léxico mínimo para un sentimiento básico de titulares (en inglés, como las noticias).
POS_WORDS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "gain", "gains",
    "upgrade", "upgraded", "record", "growth", "profit", "strong", "bullish", "buy",
    "outperform", "jump", "jumps", "rise", "rises", "boost", "wins", "positive", "high",
}
NEG_WORDS = {
    "miss", "misses", "plunge", "plunges", "drop", "drops", "fall", "falls", "crash",
    "downgrade", "downgraded", "loss", "losses", "weak", "bearish", "sell", "cut", "cuts",
    "underperform", "slump", "decline", "declines", "warn", "warns", "lawsuit", "probe",
    "negative", "low", "fear", "fears", "risk", "recall",
}


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def score_sentiment(titles: list[str]) -> tuple[float, int, int]:
    """Sentimiento básico por conteo de palabras. Devuelve (score[-1..1], pos, neg)."""
    pos = neg = 0
    for title in titles:
        for word in str(title).lower().replace(",", " ").replace(".", " ").split():
            if word in POS_WORDS:
                pos += 1
            elif word in NEG_WORDS:
                neg += 1
    total = pos + neg
    score = (pos - neg) / total if total else 0.0
    return round(score, 2), pos, neg


def fetch_news_titles(symbol: str, limit: int = 10) -> list[str]:
    """Titulares recientes vía yfinance (tolerante a cambios de formato)."""
    try:
        import yfinance as yf
        items = yf.Ticker(to_yfinance(symbol)).news or []
    except Exception:
        return []
    titles = []
    for it in items[:limit]:
        title = it.get("title") or it.get("content", {}).get("title") if isinstance(it, dict) else None
        if title:
            titles.append(title)
    return titles


def analyze(symbol: str, data, use_ai: bool = False, ai_model: str | None = None) -> dict:
    """Analiza un símbolo y devuelve métricas + veredicto.

    use_ai=True usa Claude para el sentimiento de noticias (más preciso) en vez
    del léxico básico. Si falla (sin clave o sin librería), cae al método básico.
    """
    bars = data.get_bars(symbol, limit=300, interval_minutes=None)  # ~diario
    if bars.empty or len(bars) < 60:
        return {"symbol": symbol, "error": "datos insuficientes"}

    closes = bars["close"]
    price = float(closes.iloc[-1])
    factors: list[tuple[str, int, str]] = []  # (nombre, puntos, detalle)

    # 1) Tendencia: precio vs media de 50 sesiones
    sma50 = closes.rolling(50).mean().iloc[-1]
    trend_pts = 1 if price > sma50 else -1
    factors.append(("Tendencia (precio vs SMA50)", trend_pts,
                    f"{'por encima' if trend_pts > 0 else 'por debajo'} de la media"))

    # 2) Tendencia de fondo: cruce SMA50 vs SMA200 (si hay datos)
    if len(closes) >= 200:
        sma200 = closes.rolling(200).mean().iloc[-1]
        macro_pts = 1 if sma50 > sma200 else -1
        factors.append(("Tendencia de fondo (SMA50 vs SMA200)", macro_pts,
                        "alcista (golden cross)" if macro_pts > 0 else "bajista (death cross)"))

    # 3) Momentum: RSI(14)
    rsi_val = float(rsi(closes, 14).iloc[-1])
    rsi_pts = 1 if rsi_val < 35 else (-1 if rsi_val > 70 else 0)
    rsi_state = "sobreventa (barato)" if rsi_val < 35 else ("sobrecompra (caro)" if rsi_val > 70 else "neutral")
    factors.append((f"RSI = {rsi_val:.0f}", rsi_pts, rsi_state))

    # 4) MACD (cruce)
    macd = _ema(closes, 12) - _ema(closes, 26)
    signal = _ema(macd, 9)
    macd_pts = 1 if macd.iloc[-1] > signal.iloc[-1] else -1
    factors.append(("MACD", macd_pts, "alcista" if macd_pts > 0 else "bajista"))

    # 5) Volumen: confirma el movimiento del día
    if "volume" in bars.columns and len(bars) >= 20:
        avg_vol = bars["volume"].tail(20).mean()
        last_vol = bars["volume"].iloc[-1]
        day_change = closes.iloc[-1] - closes.iloc[-2]
        if last_vol > avg_vol * 1.2:
            vol_pts = 1 if day_change > 0 else -1
            factors.append(("Volumen alto", vol_pts,
                            f"confirma {'subida' if vol_pts > 0 else 'bajada'}"))

    # 6) Posición en el rango de 52 semanas
    hi, lo = closes.max(), closes.min()
    pos52 = (price - lo) / (hi - lo) if hi > lo else 0.5
    if pos52 < 0.15:
        factors.append(("Rango anual", 1, "cerca del mínimo (posible valor)"))
    elif pos52 > 0.95:
        factors.append(("Rango anual", -1, "en máximos (riesgo de techo)"))

    # 7) Volatilidad (informativa, no puntúa dirección)
    atr_pct = average_true_range(bars, 14) / price * 100 if price else 0.0

    # 8) Noticias
    titles = fetch_news_titles(symbol)
    if titles:
        sent_score = None
        detail = ""
        if use_ai:
            # Sentimiento con IA (Claude): lee y entiende los titulares.
            try:
                from .ai_analyst import analyze_news
                ai = analyze_news(symbol, titles, model=ai_model)
                sent_score = float(ai["sentimiento"])
                detail = f"IA: {ai['etiqueta']} — {ai['resumen'][:70]}"
            except Exception as exc:  # sin clave/librería o error de red -> método básico
                detail = f"(IA no disponible: {str(exc)[:40]}) "
        if sent_score is None:
            # Método básico: conteo de palabras.
            sent_score, pos_n, neg_n = score_sentiment(titles)
            detail = detail + f"léxico +{pos_n}/-{neg_n}, sentimiento {sent_score:+.2f}"
        news_pts = 1 if sent_score > 0.2 else (-1 if sent_score < -0.2 else 0)
        factors.append((f"Noticias ({len(titles)} titulares)", news_pts, detail))

    # --- Veredicto combinado ---
    total = sum(pts for _, pts, _ in factors)
    max_abs = sum(abs(pts) for _, pts, _ in factors) or 1
    if total >= 2:
        verdict = "COMPRAR"
    elif total <= -2:
        verdict = "VENDER"
    else:
        verdict = "MANTENER"
    confidence = round(abs(total) / max_abs * 100)

    return {
        "symbol": symbol, "precio": round(price, 2), "RSI": round(rsi_val, 1),
        "ATR_%": round(atr_pct, 2), "pos_52sem_%": round(pos52 * 100),
        "factores": factors, "puntuacion": total, "veredicto": verdict,
        "confianza_%": confidence,
    }


def _print_report(r: dict) -> None:
    if "error" in r:
        print(f"\n{r['symbol']}: {r['error']}\n")
        return
    print("\n" + "=" * 60)
    print(f"ANÁLISIS {r['symbol']}  |  precio {r['precio']}  |  RSI {r['RSI']}  |  ATR {r['ATR_%']}%")
    print("=" * 60)
    for name, pts, detail in r["factores"]:
        icon = "🟢" if pts > 0 else ("🔴" if pts < 0 else "⚪")
        print(f"  {icon} {name:<38} {detail}")
    print("-" * 60)
    print(f"  VEREDICTO: {r['veredicto']}  (puntuación {r['puntuacion']:+d}, confianza {r['confianza_%']}%)")
    print("  ⚠️ Apoyo a la decisión, NO una predicción. Verifica siempre tú.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analizador multifactor (técnica + noticias)")
    parser.add_argument("symbols", nargs="+", help="uno o más símbolos: AAPL TSLA BTC/USD")
    args = parser.parse_args()

    cfg = Config()
    cfg.validate(require_broker=False)
    data = make_data_source(cfg)

    if cfg.use_ai_news:
        print(f"(Sentimiento de noticias con IA: {cfg.ai_model})")
    for symbol in args.symbols:
        try:
            _print_report(analyze(symbol, data, use_ai=cfg.use_ai_news, ai_model=cfg.ai_model))
        except Exception as exc:
            print(f"\n{symbol}: error -> {exc}\n")


if __name__ == "__main__":
    main()
