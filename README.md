# Bot de Trading Automatizado (acciones · ETF · cripto)

Bot en Python que **abre y cierra posiciones automáticamente** (acciones, ETF y
cripto) según una estrategia técnica. **Ejecuta las órdenes en
[eToro](https://api-portal.etoro.com)** a través de su API oficial, con **cuenta
demo virtual** y stop-loss/take-profit nativos.

> ℹ️ **Sin Alpaca necesaria.** Los datos de mercado para las señales se
> descargan por defecto de **Yahoo Finance (yfinance), sin ninguna clave**. Solo
> necesitas tus credenciales de eToro para ejecutar. (Opcionalmente puedes usar
> Alpaca como broker o fuente de datos, pero es totalmente opcional.)

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
# Analizador multifactor: técnica + noticias -> COMPRAR/MANTENER/VENDER
python -m tradingbot.analyzer AAPL TSLA NVDA

# Sentimiento de noticias con IA (Claude) — requiere ANTHROPIC_API_KEY
#   en .env: USE_AI_NEWS=true  (el analizador lo usa automáticamente)
python -m tradingbot.ai_analyst AAPL       # probar solo el análisis de noticias

# Screener: ¿qué activos son más APTOS para intradía (líquidos + con movimiento)?
python -m tradingbot.screener --symbols TSLA,NVDA,AAPL,MARA,SPY --days 30

# Backtest: ¿la estrategia habría funcionado en este activo?
python -m tradingbot.backtest AAPL --strategy sma
python -m tradingbot.backtest TSLA --strategy intraday --minutes 5 --capital 1000

# Simulación (NO envía órdenes, solo muestra qué haría)
python -m tradingbot.runner --once --dry-run

# Un ciclo real en PAPER (dinero ficticio)
python -m tradingbot.runner --once

# Bucle continuo en PAPER (revisa cada LOOP_INTERVAL_SECONDS)
python -m tradingbot.runner
```

### Ejecutar en eToro

El bot puede ejecutar las órdenes **en eToro** (no solo en Alpaca). En `.env`:

```ini
BROKER=etoro
ETORO_API_KEY=...          # de https://api-portal.etoro.com
ETORO_USER_KEY=...
ETORO_DEMO=true            # cuenta virtual (empieza SIEMPRE aquí)
# eToro usa IDs numéricos, no tickers. Mapea tus símbolos:
ETORO_INSTRUMENTS=TSLA:1001,NVDA:1002,BTC/USD:100000
```

```bash
python -m tradingbot.runner --once --dry-run   # simula el ciclo contra eToro
python -m tradingbot.runner --once             # opera en tu cuenta DEMO de eToro
```

Ventaja de eToro: el **stop-loss y take-profit se ejecutan de forma nativa**
(`stopLossRate`/`takeProfitRate`), así que la protección va en el propio servidor
de eToro, no depende de que el bot esté encendido.

> **Datos de mercado:** por defecto se usan datos de **Yahoo Finance
> (yfinance), SIN claves** — no hace falta Alpaca para nada. Puedes cambiar la
> fuente con `DATA_SOURCE` a `etoro` (feed nativo, requiere la ruta de velas de
> tu portal) o `alpaca` (requiere claves de Alpaca).
>
> **Rutas por verificar:** la API de eToro tiene la doc completa tras login. El
> endpoint de *apertura* está confirmado; los de *cierre*, *listado de
> posiciones* y *cuenta* están implementados pero centralizados en constantes
> `ENDPOINT_*` de `tradingbot/etoro.py` — ajústalos con lo que veas en tu portal.

### Modo intradía

Pon `STRATEGY=intraday` en `.env` y el runner cambia a velas de minutos con
RSI, dimensionando cada posición por riesgo y calculando stop-loss/take-profit:

```bash
# en .env:  STRATEGY=intraday  INTRADAY_MINUTES=5  RISK_PCT=1.0
python -m tradingbot.runner --once --dry-run   # ver el ciclo intradía sin operar
```

Cada operación se registra en `logs/trades.csv` para que midas tu ventaja real.

### Métricas del backtest

El backtest intradía simula la salida por stop-loss/take-profit dentro de cada
vela y devuelve métricas para juzgar si la estrategia tiene ventaja:

| Métrica | Qué significa |
|---|---|
| `win_rate_%` | % de operaciones ganadoras |
| `profit_factor` | dinero ganado ÷ perdido. **>1 = rentable**, <1 = pierde |
| `max_drawdown_%` | peor caída desde un máximo (el "dolor" máximo) |
| `retorno_%` | resultado total vs. `buy_hold_%` (comprar y mantener) |

Regla práctica: no pases a dinero real si el `profit_factor` no es
consistentemente **> 1.3** en varios activos y periodos. Y recuerda: el backtest
no incluye comisiones ni slippage, así que en real será peor.

Para operar con **dinero real** (solo cuando estés seguro): pon
`ALPACA_PAPER=false` en `.env` **y** ejecuta con `--live-confirm`. Sin esa
confirmación explícita el bot se niega a arrancar en real, por seguridad.

---

## Cómo funciona

```
tradingbot/
├── config.py     Carga y valida la configuración (.env)
├── datasource.py Selector de fuente de datos (yfinance / eToro / Alpaca)
├── data_yf.py    Datos de Yahoo Finance (SIN claves, por defecto)
├── data_etoro.py Datos del feed nativo de eToro
├── data.py       Datos de Alpaca (opcional)
├── analyzer.py   Análisis multifactor (tendencia+RSI+MACD+volumen+noticias)
├── ai_analyst.py Sentimiento de noticias con IA (Claude) — opcional
├── strategy.py   Señales: cruce de medias (SMA) y reversión intradía (RSI)
├── risk.py       Stop-loss / take-profit (ATR) y tamaño de posición por riesgo %
├── screener.py   Puntúa activos por idoneidad intradía (volatilidad + liquidez)
├── trade_log.py  Registra cada operación en CSV para medir tu ventaja real
├── broker.py     Ejecuta órdenes en Alpaca (abrir/cerrar)
├── etoro.py      Broker de eToro (API oficial, demo/real, SL/TP nativo)
├── instruments.py Mapa ticker<->instrumentId de eToro
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
