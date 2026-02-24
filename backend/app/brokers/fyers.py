import asyncio
import logging
from typing import List

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)


class FyersAdapter(BrokerAdapter):
    """
    Real adapter for Fyers using the fyers-apiv3 SDK.
    API docs: https://myapi.fyers.in/docsv3
    Portal: https://myapi.fyers.in/dashboard
    Auth flow:
      1. Create app on Fyers API dashboard → get app_id & secret_key
      2. Generate auth_code via OAuth redirect → exchange for access_token
      3. Store access_token in .env (valid for 1 trading day)
    Fyers symbols use format: "NSE:SYMBOL-EQ" for equities.
    """

    name = "fyers"

    @staticmethod
    def _fyers_symbol(symbol: str, exchange: str = "NSE") -> str:
        """Convert plain symbol (e.g., RELIANCE) to Fyers format (NSE:RELIANCE-EQ)."""
        return f"{exchange}:{symbol}-EQ"

    def _get_fyers(self, access_token: str = None):
        from fyers_apiv3 import fyersModel
        client_id = settings.fyers_app_id
        token = access_token or settings.fyers_access_token
        fyers = fyersModel.FyersModel(client_id=client_id, token=token, is_async=False, log_path="")
        return fyers

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        try:
            app_id = credentials.api_key or settings.fyers_app_id
            secret_key = credentials.api_secret or settings.fyers_secret_key

            if not app_id:
                return BrokerAuthResponse(
                    broker=BrokerName.FYERS, authenticated=False,
                    message="Missing FYERS_APP_ID. Set it in .env or pass via request.",
                )

            access_token = credentials.access_token or settings.fyers_access_token
            if access_token:
                from fyers_apiv3 import fyersModel
                fyers = fyersModel.FyersModel(client_id=app_id, token=access_token, is_async=False, log_path="")
                profile = await asyncio.to_thread(fyers.get_profile)
                if profile.get("s") == "ok":
                    user_data = profile.get("data", {})
                    return BrokerAuthResponse(
                        broker=BrokerName.FYERS, authenticated=True,
                        session_token=access_token,
                        user_id=user_data.get("fy_id", ""),
                        message=f"Connected to Fyers as {user_data.get('name', 'User')}",
                    )
                else:
                    return BrokerAuthResponse(
                        broker=BrokerName.FYERS, authenticated=False,
                        message=f"Fyers auth failed: {profile.get('message', 'Invalid token')}",
                    )

            # If auth_code provided via extra, exchange for access_token
            auth_code = credentials.extra.get("auth_code") if credentials.extra else None
            if auth_code and secret_key:
                from fyers_apiv3 import fyersModel
                session = fyersModel.SessionModel(
                    client_id=app_id, secret_key=secret_key,
                    redirect_uri="http://localhost:3000/callback", response_type="code",
                    grant_type="authorization_code",
                )
                session.set_token(auth_code)
                token_resp = await asyncio.to_thread(session.generate_token)
                if token_resp.get("s") == "ok":
                    new_token = token_resp["access_token"]
                    return BrokerAuthResponse(
                        broker=BrokerName.FYERS, authenticated=True,
                        session_token=new_token,
                        message="Connected to Fyers successfully",
                    )
                return BrokerAuthResponse(
                    broker=BrokerName.FYERS, authenticated=False,
                    message=f"Token exchange failed: {token_resp.get('message', '')}",
                )

            return BrokerAuthResponse(
                broker=BrokerName.FYERS, authenticated=False,
                message="Missing FYERS_ACCESS_TOKEN. Generate one from the Fyers API dashboard.",
            )

        except Exception as e:
            logger.error(f"Fyers auth failed: {e}")
            return BrokerAuthResponse(
                broker=BrokerName.FYERS, authenticated=False,
                message=f"Fyers auth failed: {str(e)}",
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        fyers = self._get_fyers(session_token)
        response = await asyncio.to_thread(fyers.holdings)
        holdings = []
        if response.get("s") == "ok" and response.get("holdings"):
            for h in response["holdings"]:
                # Fyers symbol format: "NSE:RELIANCE-EQ" → extract "RELIANCE"
                raw_symbol = h.get("symbol", "")
                symbol = raw_symbol.split(":")[-1].replace("-EQ", "") if ":" in raw_symbol else raw_symbol
                holdings.append(Holding(
                    symbol=symbol,
                    quantity=h.get("quantity", 0),
                    average_price=h.get("costPrice", 0.0),
                    current_price=h.get("ltp", 0.0),
                    pnl=h.get("pl", 0.0),
                    exchange=raw_symbol.split(":")[0] if ":" in raw_symbol else "NSE",
                ))
        return holdings

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        fyers = self._get_fyers(session_token)
        try:
            side = 1 if instruction.action in (TradeAction.BUY, TradeAction.REBALANCE) else -1
            order_data = {
                "symbol": self._fyers_symbol(instruction.symbol, instruction.exchange),
                "qty": abs(instruction.quantity),
                "type": 2 if instruction.order_type == "MARKET" else 1,  # 2=MARKET, 1=LIMIT
                "side": side,
                "productType": "CNC",
                "limitPrice": instruction.price or 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False,
            }
            response = await asyncio.to_thread(fyers.place_order, data=order_data)

            if response.get("s") == "ok":
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                    order_id=response.get("id", ""),
                    message="Order placed successfully on Fyers",
                )
            else:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message=f"Fyers order rejected: {response.get('message', '')}",
                )
        except Exception as e:
            logger.error(f"Fyers order failed for {instruction.symbol}: {e}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=f"Fyers order failed: {str(e)}",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        fyers = self._get_fyers(session_token)
        try:
            response = await asyncio.to_thread(fyers.orderBook)
            if response.get("s") == "ok":
                for order in response.get("orderBook", []):
                    if order.get("id") == order_id:
                        is_complete = order.get("status") == 2  # 2=FILLED
                        raw_sym = order.get("symbol", "")
                        symbol = raw_sym.split(":")[-1].replace("-EQ", "") if ":" in raw_sym else raw_sym
                        return OrderResult(
                            symbol=symbol,
                            action=TradeAction.BUY if order.get("side") == 1 else TradeAction.SELL,
                            quantity=order.get("qty", 0),
                            status=OrderStatus.EXECUTED if is_complete else OrderStatus.FAILED,
                            order_id=order_id,
                            executed_price=order.get("tradedPrice"),
                            message=order.get("message", ""),
                        )
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message="Order not found in order book",
            )
        except Exception as e:
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message=f"Failed to fetch order status: {str(e)}",
            )
