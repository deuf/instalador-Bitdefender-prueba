# Bot de Trading Automatizado (acciones · ETF · cripto)

Bot en Python que **abre y cierra posiciones automáticamente** según una
estrategia de cruce de medias móviles. Ejecuta las órdenes a través de
[**Alpaca**](https://alpaca.markets), un bróker con API oficial y gratuita que
soporta **acciones, ETF y cripto** e incluye **paper trading** (dinero ficticio).

> ℹ️ **Sobre eToro:** eToro **sí ofrece una API oficial** (portal de
> desarrolladores en <https://api-portal.etoro.com>), con endpoints REST para
> abrir/cerrar posiciones y una **cuenta demo virtual**. Este proyecto incluye
> un adaptador de eToro (`tradingbot/etoro.py`) además del de Alpaca. Alpaca se
> usa como opción principal porque su *paper trading* y sus datos históricos son
> gratuitos y muy cómodos para desarrollar y hacer backtest; puedes ejecutar en
> eToro cuando lo tengas validado.

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
# Screener: ¿qué activos son más APTOS para intradía (líquidos + con movimiento)?
python -m tradingbot.screener --symbols TSLA,NVDA,AAPL,MARA,SPY --days 30

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
├── strategy.py   Señales: cruce de medias (SMA) y reversión intradía (RSI)
├── risk.py       Stop-loss / take-profit (ATR) y tamaño de posición por riesgo %
├── screener.py   Puntúa activos por idoneidad intradía (volatilidad + liquidez)
├── trade_log.py  Registra cada operación en CSV para medir tu ventaja real
├── broker.py     Ejecuta órdenes en Alpaca (abrir/cerrar)
├── etoro.py      Adaptador para la API oficial de eToro (demo/real, con SL/TP)
├── runner.py     Bucle principal: revisa la watchlist y actúa
└── backtest.py   Prueba la estrategia con datos históricos

**Estrategias disponibles:**
- `sma_crossover_signal` — cruce de medias (tendencia), para velas diarias.
- `intraday_signal` — reversión a la media con **RSI**, para velas de minutos:
  compra al salir de sobreventa, cierra al salir de sobrecompra.

**Gestión de riesgo (`risk.py`):**
- `stop_take_levels` — calcula stop-loss y take-profit según el ATR (volatilidad).
- `position_notional` — dimensiona la posición para arriesgar solo un % fijo del
  capital por operación (regla de oro: 1–2 %).
```

## Trading intradía: qué esperar (lee esto)

Quieres operar **intradía** (abrir y cerrar en el mismo día). Es lo más difícil
del trading. Datos que debes tener en cuenta:

- **La mayoría de traders intradía minoristas pierden dinero.** Estudios sobre
  brokers muestran que ~70–85 % terminan en pérdidas. No es opinión, es lo que
  reflejan los propios avisos de riesgo regulatorios.
- **Regla PDT (EE. UU.):** para hacer más de 3 operaciones intradía en 5 días
  con un bróker estadounidense necesitas **≥ 25.000 USD** en la cuenta.
- **Comisiones y spread** se comen los márgenes pequeños del intradía. En demo no
  se notan; en real, sí.

Por eso este proyecto **no promete ganancias**. Lo que te da son herramientas
para trabajar con método:

1. **Screener** → elige el terreno (activos líquidos y con movimiento).
2. **Backtest** → comprueba si tu estrategia tuvo ventaja en el pasado.
3. **Paper trading** → valida en tiempo real sin arriesgar.
4. **Gestión de riesgo** → nunca arriesgar más de un % pequeño por operación.

Solo cuando 2 y 3 sean consistentes durante semanas tiene sentido pasar a real.

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
