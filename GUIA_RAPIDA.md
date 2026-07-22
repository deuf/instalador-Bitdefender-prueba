# 🚀 Guía rápida — Cómo ejecutar el bot (desde cero)

Esta guía asume que **nunca** has usado Python ni la terminal. Sigue los pasos
en orden. El bot se ejecuta **en TU ordenador**, no en la web.

---

## Paso 1 — Instalar Python

- **Windows:** descarga Python en <https://www.python.org/downloads/> y, al
  instalar, **marca la casilla "Add Python to PATH"**.
- **Mac:** descarga Python en <https://www.python.org/downloads/> (o `brew install python`).

Para comprobar que quedó instalado, abre la terminal y escribe:

```bash
python --version
```

(En Mac/Linux puede ser `python3 --version`.) Debe mostrar algo como `Python 3.12`.

> **¿Cómo abrir la terminal?**
> - Windows: menú inicio → escribe "cmd" → Enter.
> - Mac: Cmd+Espacio → escribe "Terminal" → Enter.

---

## Paso 2 — Descargar el código

En GitHub, en la página del repositorio (rama `claude/analisis-mercado-zimhne`):

- Botón verde **"Code" → "Download ZIP"**, y descomprímelo. Anota la carpeta.

O si tienes git instalado:

```bash
git clone <URL-del-repo>
cd instalador-Bitdefender-prueba
```

Luego, en la terminal, **entra en la carpeta** del proyecto:

```bash
cd ruta/donde/lo/descomprimiste
```

---

## Paso 3 — Instalar las dependencias

Dentro de la carpeta del proyecto:

```bash
pip install -r requirements.txt
```

(Si `pip` no funciona, prueba `pip3 install -r requirements.txt`.)

---

## Paso 4 — Conseguir claves GRATIS (para los datos de mercado)

El bot necesita datos de precios. La fuente gratuita es **Alpaca** (no hace
falta operar ni poner dinero, solo leer datos):

1. Crea cuenta en <https://alpaca.markets>.
2. Cambia a **"Paper Trading"** (arriba).
3. **Generate New Keys** → copia la *API Key* y la *Secret Key*.

---

## Paso 5 — Configurar el archivo `.env`

1. Copia el archivo de ejemplo:

   ```bash
   cp .env.example .env          # en Windows: copy .env.example .env
   ```

2. Abre `.env` con el Bloc de notas y pega tus claves. Para la **primera
   prueba**, deja lo más sencillo posible:

   ```ini
   ALPACA_API_KEY=tu_clave_de_alpaca
   ALPACA_SECRET_KEY=tu_secret_de_alpaca
   ALPACA_PAPER=true
   BROKER=alpaca
   STRATEGY=intraday
   ```

---

## Paso 6 — ¡Ejecutar! (empieza SIEMPRE por aquí)

### a) Ver si la estrategia funciona en el pasado (no arriesga nada)

```bash
python -m tradingbot.backtest AAPL --strategy intraday
```

Verás métricas como `profit_factor` y `retorno_%`. **>1 = rentable.**

### b) Ver qué activos son mejores para intradía

```bash
python -m tradingbot.screener --symbols TSLA,NVDA,AAPL,SPY
```

### c) Simular el bot en vivo SIN enviar órdenes

```bash
python -m tradingbot.runner --once --dry-run
```

Muestra qué compraría/vendería, pero **no ejecuta nada**.

### d) Operar en la cuenta DEMO (dinero ficticio)

```bash
python -m tradingbot.runner --once
```

---

## Paso 7 (más adelante) — Ejecutar en eToro

Cuando tengas **acceso de desarrollador** de eToro
(<https://api-portal.etoro.com>) y sepas los `instrumentId` de tus activos,
cambia en `.env`:

```ini
BROKER=etoro
ETORO_API_KEY=...
ETORO_USER_KEY=...
ETORO_DEMO=true
ETORO_INSTRUMENTS=TSLA:1001,BTC/USD:100000
```

Y ejecuta igual: `python -m tradingbot.runner --once --dry-run` primero.

---

## ⚠️ Orden recomendado (no te saltes pasos)

1. **Backtest** → ¿tiene ventaja la estrategia?
2. **Dry-run** → ¿el bot decide bien?
3. **Demo (paper)** → semanas operando sin riesgo.
4. **Dinero real** → solo si 1-3 fueron bien. Y con poco dinero al principio.

**Nunca** pases a dinero real sin haber pasado por 1, 2 y 3.

---

## ❓ Si algo falla

- `command not found: python` → usa `python3`.
- `No module named tradingbot` → asegúrate de estar **dentro de la carpeta**
  del proyecto al ejecutar los comandos.
- `Faltan ALPACA_API_KEY...` → revisa que el `.env` tiene tus claves y está en
  la carpeta del proyecto.
- Cualquier otro error: cópiamelo tal cual y te ayudo.
