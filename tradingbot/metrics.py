"""Métricas de rendimiento para evaluar una estrategia con honestidad."""

from __future__ import annotations


def max_drawdown_pct(equity_curve: list[float]) -> float:
    """Peor caída desde un máximo (en %). Mide el dolor máximo que habrías sufrido."""
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = (value - peak) / peak * 100 if peak else 0.0
        worst = min(worst, drawdown)
    return round(worst, 2)


def summarize_trades(pnls: list[float], capital: float, final_equity: float) -> dict:
    """Resume una lista de resultados (PnL por operación) en métricas clave."""
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)

    return {
        "operaciones": n,
        "aciertos": len(wins),
        "win_rate_%": round(len(wins) / n * 100, 1) if n else 0.0,
        "ganancia_media": round(gross_win / len(wins), 2) if wins else 0.0,
        "perdida_media": round(-gross_loss / len(losses), 2) if losses else 0.0,
        # Profit factor = dinero ganado / dinero perdido. >1 = rentable; <1 = pierde.
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else float("inf"),
        "retorno_%": round((final_equity / capital - 1) * 100, 2),
    }
