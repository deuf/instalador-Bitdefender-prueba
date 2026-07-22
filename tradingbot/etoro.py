"""Adaptador para la API oficial de eToro (acciones, ETF y cripto).

eToro SÍ ofrece una API oficial. Para usarla necesitas:
  1. Cuenta eToro y solicitar acceso de desarrollador en https://api-portal.etoro.com
  2. Tus credenciales: API key (x-api-key) y User key (x-user-key)

MODO DEMO: eToro expone un endpoint de cuenta virtual (`/demo/`) para practicar
sin dinero real. Este adaptador lo usa por defecto.

⚠️ AVISO SOBRE LOS ENDPOINTS
La documentación completa de eToro está tras login, así que las rutas exactas
de CIERRE y de CONSULTA de posiciones deben verificarse contra tu portal oficial
antes de operar en real. Las he centralizado abajo (constantes ENDPOINT_*) para
que sea trivial ajustarlas. El endpoint de APERTURA y las cabeceras están
confirmados por documentación pública.
"""

from __future__ import annotations

import requests

BASE_URL = "https://public-api.etoro.com"

# Rutas de ejecución. La variante /demo/ opera sobre la cuenta virtual.
ENDPOINT_ORDERS = "/api/v2/trading/execution/orders"
ENDPOINT_ORDERS_DEMO = "/api/v2/trading/execution/demo/orders"
# ⚠️ VERIFICAR estas dos contra tu portal oficial antes de usar en real:
ENDPOINT_POSITIONS = "/api/v1/trading/portfolio/positions"
ENDPOINT_POSITIONS_DEMO = "/api/v1/trading/portfolio/demo/positions"


class EToroBroker:
    """Cliente mínimo de la API de eToro para abrir/cerrar posiciones."""

    def __init__(self, api_key: str, user_key: str, demo: bool = True, timeout: int = 20) -> None:
        if not api_key or not user_key:
            raise ValueError(
                "Faltan credenciales de eToro (ETORO_API_KEY / ETORO_USER_KEY). "
                "Solicítalas en https://api-portal.etoro.com"
            )
        self.demo = demo
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "x-api-key": api_key,
                "x-user-key": user_key,
                "Content-Type": "application/json",
            }
        )

    @property
    def mode_label(self) -> str:
        return "DEMO (virtual)" if self.demo else "REAL (dinero real)"

    def _orders_url(self) -> str:
        return BASE_URL + (ENDPOINT_ORDERS_DEMO if self.demo else ENDPOINT_ORDERS)

    def _positions_url(self) -> str:
        return BASE_URL + (ENDPOINT_POSITIONS_DEMO if self.demo else ENDPOINT_POSITIONS)

    def open_position(self, instrument_id: int, amount_usd: float, buy: bool = True) -> dict:
        """Abre una posición de mercado por un importe en USD.

        instrument_id: el identificador numérico del activo en eToro (no el ticker).
        """
        body = {
            "action": "open",
            "transaction": "buy" if buy else "sell",
            "instrumentId": int(instrument_id),
            "orderType": "mkt",           # orden a mercado
            "amount": round(amount_usd, 2),
            "orderCurrency": "usd",
        }
        resp = self._session.post(self._orders_url(), json=body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def close_position(self, position_id: str) -> dict:
        """Cierra una posición abierta por su positionId.

        ⚠️ Verifica el formato del cuerpo/ruta de cierre en tu portal oficial.
        """
        body = {"action": "close", "positionId": str(position_id)}
        resp = self._session.post(self._orders_url(), json=body, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> list[dict]:
        """Lista las posiciones abiertas. ⚠️ Verifica la ruta en tu portal."""
        resp = self._session.get(self._positions_url(), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # La forma exacta de la respuesta puede variar; normalizamos a lista.
        if isinstance(data, dict):
            return data.get("positions", data.get("data", []))
        return data
