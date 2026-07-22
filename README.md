# Bot de Trading Automatizado (acciones · ETF · cripto)

Bot en Python que **abre y cierra posiciones automáticamente** según una
estrategia de cruce de medias móviles. Ejecuta las órdenes a través de
[**Alpaca**](https://alpaca.markets), un bróker con API oficial y gratuita que
soporta **acciones, ETF y cripto** e incluye **paper trading** (dinero ficticio).

> ⚠️ **Sobre eToro:** eToro **no ofrece una API pública de trading** para
> minoristas. Automatizarlo requeriría simular clicks en su web, lo que **viola
> sus Términos de Servicio** y puede acabar en el **baneo de tu cuenta**. Por eso
> este proyecto usa Alpaca, que sí está pensado para automatización. Si más
> adelante quieres seguir traders de eToro, mira su función nativa de *copy-trading*.

---

## ⚠️ Lee esto antes de nada

- **Ningún bot garantiza ganancias.** Automatizar una estrategia mala solo hace
  que pierdas dinero más rápido.
- **Empieza SIEMPRE en paper trading** (`ALPACA_PAPER=true`). No pases a dinero
  real hasta que la estrategia demuestre resultados en demo durante semanas.
- La estrategia incluida (cruce de medias, SMA) es un **punto de partida
  educativo**, no un sistema ganador probado.
- Operar con dinero real conlleva **riesgo de pérdidas**. Tú eres el único
  responsable de tus decisiones.

---

## Instalación

```bash
# 1. Instala dependencias
pip install -r requirements.txt

# 2. Configura tus claves
cp .env.example .env
# edita .env y pega tus claves de PAPER de Alpaca
```

### Cómo conseguir claves de Alpaca (gratis)

1. Crea una cuenta en <https://alpaca.markets>.
2. En el panel, cambia a **Paper Trading**.
3. Ve a *Home → Generate New Keys* y copia `API Key` y `Secret Key`.
4. Pégalas en tu archivo `.env` (`ALPACA_API_KEY` y `ALPACA_SECRET_KEY`).

---

## Uso

```bash
# Backtest: ¿la estrategia habría funcionado en este activo?
python -m tradingbot.backtest BTC/USD
python -m tradingbot.backtest AAPL --fast 10 --slow 30 --capital 1000

# Simulación (NO envía órdenes, solo muestra qué haría)
python -m tradingbot.runner --once --dry-run

# Un ciclo real en PAPER (dinero ficticio)
python -m tradingbot.runner --once

# Bucle continuo en PAPER (revisa cada LOOP_INTERVAL_SECONDS)
python -m tradingbot.runner
```

Para operar con **dinero real** (solo cuando estés seguro): pon
`ALPACA_PAPER=false` en `.env` **y** ejecuta con `--live-confirm`. Sin esa
confirmación explícita el bot se niega a arrancar en real, por seguridad.

---

## Cómo funciona

```
tradingbot/
├── config.py     Carga y valida la configuración (.env)
├── data.py       Descarga precios históricos (acciones/ETF y cripto)
├── strategy.py   Lógica de la señal (cruce de medias SMA)
├── broker.py     Ejecuta órdenes en Alpaca (abrir/cerrar)
├── runner.py     Bucle principal: revisa la watchlist y actúa
└── backtest.py   Prueba la estrategia con datos históricos
```

**Estrategia (SMA crossover):**
- **COMPRA** cuando la media rápida cruza por encima de la lenta.
- **VENDE (cierra)** cuando la media rápida cruza por debajo de la lenta.

**Gestión de riesgo incluida:**
- Importe fijo por operación (`TRADE_NOTIONAL_USD`).
- Límite de posiciones abiertas simultáneas (`MAX_OPEN_POSITIONS`).
- Barrera anti-accidentes para no operar en real sin confirmación.

---

## Personalizar

- **Otros activos:** edita `WATCHLIST` en `.env` (cripto lleva `/`: `BTC/USD`;
  acciones/ETF no: `AAPL`, `SPY`).
- **Otra sensibilidad:** ajusta `SMA_FAST` / `SMA_SLOW`.
- **Tu propia estrategia:** sustituye la función `sma_crossover_signal` en
  `strategy.py` por tu lógica (RSI, momentum, etc.). El resto del bot no cambia.

---

## Próximos pasos sugeridos

1. Añadir **stop-loss / take-profit** automáticos.
2. Registrar operaciones en CSV para analizar resultados.
3. Notificaciones (Telegram/email) al abrir/cerrar.
4. Backtest sobre varios activos a la vez con métricas de riesgo (drawdown, Sharpe).

Dímelo y lo implementamos.
