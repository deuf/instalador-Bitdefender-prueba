"""Capa de ejecución: habla con Alpaca para consultar cuenta y enviar órdenes."""

from __future__ import annotations

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .symbols import is_crypto


class Broker:
    """Envoltura fina sobre TradingClient de Alpaca."""

    def __init__(self, api_key: str, secret_key: str, paper: bool = True) -> None:
        self._client = TradingClient(api_key, secret_key, paper=paper)
        self.paper = paper

    # --- Consultas ---
    def account_summary(self) -> dict:
        acct = self._client.get_account()
        return {
            "equity": float(acct.equity),
            "cash": float(acct.cash),
            "buying_power": float(acct.buying_power),
            "currency": acct.currency,
        }

    def open_symbols(self) -> set[str]:
        """Conjunto de símbolos con posición abierta actualmente."""
        return {p.symbol for p in self._client.get_all_positions()}

    def has_position(self, symbol: str) -> bool:
        # Alpaca reporta cripto sin la barra (BTCUSD); normalizamos para comparar.
        normalized = symbol.replace("/", "")
        return any(
            p.symbol.replace("/", "") == normalized
            for p in self._client.get_all_positions()
        )

    # --- Órdenes ---
    def open_long(
        self,
        symbol: str,
        notional_usd: float,
        stop_loss_rate: float | None = None,   # noqa: ARG002 (interfaz común con eToro)
        take_profit_rate: float | None = None,  # noqa: ARG002
    ) -> str:
        """Abre una posición larga por un importe en dólares (fraccional).

        stop_loss_rate/take_profit_rate se aceptan para compartir interfaz con el
        broker de eToro, pero Alpaca aún no los aplica aquí (requiere bracket
        orders; es el siguiente paso). Sí se registran en el log de operaciones.
        """
        tif = TimeInForce.GTC if is_crypto(symbol) else TimeInForce.DAY
        order = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional_usd, 2),
            side=OrderSide.BUY,
            time_in_force=tif,
        )
        result = self._client.submit_order(order)
        return str(result.id)

    def close(self, symbol: str) -> str:
        """Cierra por completo la posición del símbolo."""
        result = self._client.close_position(symbol.replace("/", ""))
        return str(result.id)
