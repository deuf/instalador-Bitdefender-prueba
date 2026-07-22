"""Bucle principal del bot: revisa la watchlist y abre/cierra posiciones.

Uso:
    python -m tradingbot.runner --once            # un solo ciclo (recomendado para probar)
    python -m tradingbot.runner                   # bucle continuo
    python -m tradingbot.runner --dry-run         # NO envía órdenes, solo muestra qué haría
    python -m tradingbot.runner --live-confirm    # necesario para operar con dinero REAL
"""

from __future__ import annotations

import argparse
import logging
import time

from .broker import Broker
from .config import Config
from .data import MarketData
from .strategy import Signal, sma_crossover_signal

log = logging.getLogger("tradingbot")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_cycle(cfg: Config, data: MarketData, broker: Broker | None, dry_run: bool) -> None:
    """Un ciclo: para cada símbolo calcula la señal y actúa según la posición."""
    open_symbols = broker.open_symbols() if broker else set()
    log.info("Posiciones abiertas: %s", sorted(open_symbols) or "ninguna")

    for symbol in cfg.watchlist:
        try:
            closes = data.get_closes(symbol, limit=cfg.sma_slow * 3)
            signal = sma_crossover_signal(closes, cfg.sma_fast, cfg.sma_slow)
            has_pos = broker.has_position(symbol) if broker else False
            price = f"{closes.iloc[-1]:.2f}" if len(closes) else "?"
            log.info("%-10s precio=%s  señal=%s  posición=%s", symbol, price, signal.value, has_pos)

            if signal is Signal.BUY and not has_pos:
                if len(open_symbols) >= cfg.max_open_positions:
                    log.info("  -> COMPRA omitida: alcanzado MAX_OPEN_POSITIONS (%d)", cfg.max_open_positions)
                    continue
                if dry_run or broker is None:
                    log.info("  -> [DRY-RUN] compraría %s por %.2f USD", symbol, cfg.trade_notional_usd)
                else:
                    oid = broker.open_long(symbol, cfg.trade_notional_usd)
                    open_symbols.add(symbol)
                    log.info("  -> COMPRA enviada (%.2f USD). Orden %s", cfg.trade_notional_usd, oid)

            elif signal is Signal.SELL and has_pos:
                if dry_run or broker is None:
                    log.info("  -> [DRY-RUN] cerraría posición de %s", symbol)
                else:
                    oid = broker.close(symbol)
                    open_symbols.discard(symbol)
                    log.info("  -> CIERRE enviado. Orden %s", oid)

        except Exception as exc:  # no dejamos que un símbolo tumbe todo el ciclo
            log.error("Error procesando %s: %s", symbol, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de trading SMA sobre Alpaca")
    parser.add_argument("--once", action="store_true", help="ejecuta un solo ciclo y termina")
    parser.add_argument("--dry-run", action="store_true", help="no envía órdenes, solo simula")
    parser.add_argument(
        "--live-confirm",
        action="store_true",
        help="confirmación explícita OBLIGATORIA para operar con dinero real",
    )
    args = parser.parse_args()

    _setup_logging()
    cfg = Config()
    cfg.validate()

    # Barrera de seguridad: nunca operar en real sin confirmación explícita.
    if not cfg.paper and not args.live_confirm and not args.dry_run:
        raise SystemExit(
            "ABORTADO: ALPACA_PAPER=false (dinero real) pero no pasaste --live-confirm.\n"
            "Si de verdad quieres operar con dinero real, añade --live-confirm."
        )

    log.info("=" * 60)
    log.info("Bot de trading — modo %s%s", cfg.mode_label, "  [DRY-RUN]" if args.dry_run else "")
    log.info("Watchlist: %s", ", ".join(cfg.watchlist))
    log.info("Estrategia: SMA %d/%d | %.0f USD/op | máx %d posiciones",
             cfg.sma_fast, cfg.sma_slow, cfg.trade_notional_usd, cfg.max_open_positions)
    log.info("=" * 60)

    data = MarketData(cfg.api_key, cfg.secret_key)
    broker = Broker(cfg.api_key, cfg.secret_key, paper=cfg.paper)

    acct = broker.account_summary()
    log.info("Cuenta: equity=%.2f %s | buying_power=%.2f",
             acct["equity"], acct["currency"], acct["buying_power"])

    if args.once:
        run_cycle(cfg, data, broker, args.dry_run)
        return

    log.info("Bucle continuo cada %d s. Ctrl+C para parar.", cfg.loop_interval_seconds)
    try:
        while True:
            run_cycle(cfg, data, broker, args.dry_run)
            time.sleep(cfg.loop_interval_seconds)
    except KeyboardInterrupt:
        log.info("Detenido por el usuario.")


if __name__ == "__main__":
    main()
