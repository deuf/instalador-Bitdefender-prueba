"""Bucle principal del bot: revisa la watchlist y abre/cierra posiciones.

Soporta dos estrategias (config STRATEGY):
  - "sma":      cruce de medias sobre velas diarias (tendencia).
  - "intraday": reversión con RSI sobre velas de minutos + gestión de riesgo
                (stop-loss/take-profit por ATR y tamaño por % de capital).

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

from .config import Config
from .datasource import make_data_source
from .risk import position_notional, stop_take_levels
from .strategy import (
    Signal,
    average_true_range,
    intraday_signal,
    sma_crossover_signal,
)
from .trade_log import TradeLog

log = logging.getLogger("tradingbot")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _compute_signal(cfg: Config, data, symbol: str):
    """Devuelve (señal, precio_actual, atr). atr solo para intradía."""
    if cfg.strategy == "intraday":
        bars = data.get_bars(symbol, limit=max(cfg.rsi_period * 4, 60),
                             interval_minutes=cfg.intraday_minutes)
        if bars.empty:
            return Signal.HOLD, None, 0.0
        signal = intraday_signal(bars["close"], cfg.rsi_period, cfg.rsi_oversold, cfg.rsi_overbought)
        atr = average_true_range(bars, cfg.rsi_period)
        return signal, float(bars["close"].iloc[-1]), atr

    closes = data.get_closes(symbol, limit=cfg.sma_slow * 3)
    if len(closes) == 0:
        return Signal.HOLD, None, 0.0
    signal = sma_crossover_signal(closes, cfg.sma_fast, cfg.sma_slow)
    return signal, float(closes.iloc[-1]), 0.0


def _size_position(cfg: Config, equity: float, buying_power: float, price: float, atr: float):
    """Calcula (notional, stop_loss, take_profit) según la estrategia.

    - intraday: dimensiona por riesgo (% del capital) con SL/TP por ATR.
    - sma:      importe fijo (TRADE_NOTIONAL_USD), sin SL/TP calculado.
    """
    if cfg.strategy == "intraday" and atr > 0 and price > 0:
        levels = stop_take_levels(price, atr, "buy", cfg.sl_atr_mult, cfg.tp_atr_mult)
        notional = position_notional(
            equity, cfg.risk_pct, price, levels.stop_loss, max_notional=buying_power * 0.95
        )
        return notional, levels.stop_loss, levels.take_profit
    return cfg.trade_notional_usd, None, None


def run_cycle(cfg, data, broker, dry_run, tlog, account):
    """Un ciclo: para cada símbolo calcula la señal y actúa según la posición."""
    open_symbols = broker.open_symbols() if broker else set()
    log.info("Posiciones abiertas: %s", sorted(open_symbols) or "ninguna")

    for symbol in cfg.watchlist:
        try:
            signal, price, atr = _compute_signal(cfg, data, symbol)
            has_pos = broker.has_position(symbol) if broker else False
            price_str = f"{price:.2f}" if price else "?"
            log.info("%-10s precio=%s  señal=%s  posición=%s", symbol, price_str, signal.value, has_pos)

            if signal is Signal.BUY and not has_pos:
                if len(open_symbols) >= cfg.max_open_positions:
                    log.info("  -> COMPRA omitida: alcanzado MAX_OPEN_POSITIONS (%d)", cfg.max_open_positions)
                    continue
                notional, sl, tp = _size_position(
                    cfg, account["equity"], account["buying_power"], price or 0.0, atr
                )
                risk_note = f"SL={sl} TP={tp}" if sl else ""
                if dry_run or broker is None:
                    log.info("  -> [DRY-RUN] compraría %s por %.2f USD  %s", symbol, notional, risk_note)
                else:
                    # eToro ejecuta el SL/TP de forma nativa; Alpaca los ignora (por ahora).
                    oid = broker.open_long(symbol, notional, stop_loss_rate=sl, take_profit_rate=tp)
                    open_symbols.add(symbol)
                    log.info("  -> COMPRA enviada (%.2f USD). Orden %s  %s", notional, oid, risk_note)
                tlog.record(symbol, "buy", "open", price or 0.0, notional,
                            signal.value, cfg.mode_label, risk_note + (" [dry]" if dry_run else ""))

            elif signal is Signal.SELL and has_pos:
                if dry_run or broker is None:
                    log.info("  -> [DRY-RUN] cerraría posición de %s", symbol)
                else:
                    oid = broker.close(symbol)
                    open_symbols.discard(symbol)
                    log.info("  -> CIERRE enviado. Orden %s", oid)
                tlog.record(symbol, "sell", "close", price or 0.0, 0.0,
                            signal.value, cfg.mode_label, "[dry]" if dry_run else "")

        except Exception as exc:  # no dejamos que un símbolo tumbe todo el ciclo
            log.error("Error procesando %s: %s", symbol, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de trading sobre Alpaca")
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
    if cfg.is_real_money and not args.live_confirm and not args.dry_run:
        raise SystemExit(
            f"ABORTADO: configuración de DINERO REAL (broker={cfg.broker}) pero no pasaste "
            "--live-confirm.\nSi de verdad quieres operar con dinero real, añade --live-confirm."
        )

    log.info("=" * 60)
    log.info("Bot de trading — modo %s%s", cfg.mode_label, "  [DRY-RUN]" if args.dry_run else "")
    log.info("Watchlist: %s", ", ".join(cfg.watchlist))
    if cfg.strategy == "intraday":
        log.info("Estrategia: INTRADÍA RSI(%d) %g/%g | velas %dm | riesgo %.1f%%/op | máx %d pos",
                 cfg.rsi_period, cfg.rsi_oversold, cfg.rsi_overbought,
                 cfg.intraday_minutes, cfg.risk_pct, cfg.max_open_positions)
    else:
        log.info("Estrategia: SMA %d/%d | %.0f USD/op | máx %d posiciones",
                 cfg.sma_fast, cfg.sma_slow, cfg.trade_notional_usd, cfg.max_open_positions)
    log.info("=" * 60)

    # Fuente de datos de mercado (según DATA_SOURCE; por defecto yfinance).
    data = make_data_source(cfg)
    log.info("Fuente de datos: %s", cfg.data_source)

    # Broker de EJECUCIÓN según configuración (imports perezosos).
    if cfg.broker == "etoro":
        from .etoro import EToroBroker
        from .instruments import Instruments
        instruments = Instruments(cfg.etoro_instruments)
        broker = EToroBroker(cfg.etoro_api_key, cfg.etoro_user_key,
                             demo=cfg.etoro_demo, instruments=instruments)
        log.info("Ejecutando en eToro | instrumentos: %s", ", ".join(instruments.symbols()))
    else:
        from .broker import Broker
        broker = Broker(cfg.api_key, cfg.secret_key, paper=cfg.paper)

    tlog = TradeLog()

    account = broker.account_summary()
    log.info("Cuenta: equity=%.2f %s | buying_power=%.2f",
             account["equity"], account["currency"], account["buying_power"])

    if args.once:
        run_cycle(cfg, data, broker, args.dry_run, tlog, account)
        return

    log.info("Bucle continuo cada %d s. Ctrl+C para parar.", cfg.loop_interval_seconds)
    try:
        while True:
            account = broker.account_summary()  # refresca equity cada ciclo
            run_cycle(cfg, data, broker, args.dry_run, tlog, account)
            time.sleep(cfg.loop_interval_seconds)
    except KeyboardInterrupt:
        log.info("Detenido por el usuario.")


if __name__ == "__main__":
    main()
