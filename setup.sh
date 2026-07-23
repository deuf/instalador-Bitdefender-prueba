#!/usr/bin/env bash
# =============================================================
#  Instalador del bot de trading para Linux (Ubuntu/Debian)
#  Uso:  bash setup.sh
# =============================================================
set -e  # aborta si algo falla

echo "==> 1/5  Comprobando Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "    Python 3 no está instalado. Instalándolo (requiere sudo)..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi
python3 --version

echo "==> 2/5  Creando entorno virtual (.venv)..."
python3 -m venv .venv

echo "==> 3/5  Activando entorno e instalando dependencias..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

echo "==> 4/5  Preparando el archivo de configuración .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "    Creado .env desde la plantilla. Edítalo con tus claves de eToro."
else
    echo "    Ya existe .env, no lo toco."
fi

echo "==> 5/5  Listo. Prueba rápida (backtest, sin claves):"
echo ""
echo "    source .venv/bin/activate"
echo "    python -m tradingbot.backtest AAPL --strategy intraday"
echo ""
echo "Todo instalado. Recuerda activar el entorno con 'source .venv/bin/activate'"
echo "cada vez que abras una terminal nueva."
