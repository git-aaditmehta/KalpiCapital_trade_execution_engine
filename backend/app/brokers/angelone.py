import asyncio
import logging
from typing import List

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)


class AngelOneAdapter(BrokerAdapter):
    """
    Real adapter for Angel One using the SmartAPI Python SDK.
    API docs: https://smartapi.angelone.in/docs
    Portal: https://smartapi.angelone.in/
    Auth flow:
      1. Create app on SmartAPI portal → get api_key
      2. Use client_id (Angel One demat ID) + password + TOTP to login
      3. SDK returns jwt_token (session token)
    Angel One uses symbol tokens (numeric) for order placement.
    The `tradingsymbol` and `symboltoken` must both be provided.
    """

    name = "angelone"

    # Common symbol → token mapping for Angel One (NSE equity)
    # Full list: https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json
    SYMBOL_TOKENS = {
        "RELIANCE": "2885", "TCS": "11536", "INFY": "1594",
        "HDFCBANK": "1333", "ICICIBANK": "4963", "ITC": "1660",
        "SBIN": "3045", "TATAMOTORS": "3456", "WIPRO": "14977",
        "BHARTIARTL": "10604", "KOTAKBANK": "1922", "LT": "11483",
        "AXISBANK": "5900", "MARUTI": "10999", "BAJFINANCE": "317",
        "HCLTECH": "7229", "SUNPHARMA": "3351", "TITAN": "3506",
        "ULTRACEMCO": "11532", "ASIANPAINT": "236", "NESTLEIND": "17963",
        "ADANIENT": "25", "ADANIPORTS": "15083", "POWERGRID": "14977",
        "NTPC": "11630", "ONGC": "2475", "JSWSTEEL": "11723",
        "TATASTEEL": "3499", "HINDALCO": "1363", "TECHM": "13538",
        "NHPC": "1756", "COALINDIA": "20374", "BPCL": "526",
    }

    def _get_smart_api(self, jwt_token: str = None):
        from SmartApi import SmartConnect
        api_key = settings.angelone_api_key
        obj = SmartConnect(api_key=api_key)
        if jwt_token:
            obj.setAccessToken(jwt_token)
        return obj

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        try:
            api_key = credentials.api_key or settings.angelone_api_key
            client_id = credentials.client_id or settings.angelone_client_id
            password = settings.angelone_password
            totp_secret = settings.angelone_totp_secret

            if not api_key or not client_id:
                return BrokerAuthResponse(
                    broker=BrokerName.ANGELONE, authenticated=False,
                    message="Missing ANGELONE_API_KEY or ANGELONE_CLIENT_ID. Set them in .env.",
                )

            # If access_token passed directly, validate it
            if credentials.access_token:
                obj = self._get_smart_api(credentials.access_token)
                profile = await asyncio.to_thread(obj.getProfile, {"exchange": "NSE"})
                if profile.get("status"):
                    return BrokerAuthResponse(
                        broker=BrokerName.ANGELONE, authenticated=True,
                        session_token=credentials.access_token,
                        user_id=client_id,
                        message=f"Connected to Angel One as {profile.get('data', {}).get('name', client_id)}",
                    )

            # Login with client_id + password + TOTP
            if not password:
                return BrokerAuthResponse(
                    broker=BrokerName.ANGELONE, authenticated=False,
                    message="Missing ANGELONE_PASSWORD. Set it in .env for auto-login.",
                )

            from SmartApi import SmartConnect
            obj = SmartConnect(api_key=api_key)

            totp_value = None
            if totp_secret:
                import pyotp
                totp_value = pyotp.TOTP(totp_secret).now()
            else:
                # If no TOTP secret, check if user provided it via extra
                totp_value = credentials.extra.get("totp") if credentials.extra else None

            if not totp_value:
                return BrokerAuthResponse(
                    broker=BrokerName.ANGELONE, authenticated=False,
                    message="Missing TOTP. Set ANGELONE_TOTP_SECRET in .env or pass totp in extra.",
                )

            data = await asyncio.to_thread(
                obj.generateSession, client_id, password, totp_value
            )

            if data.get("status"):
                jwt_token = data["data"]["jwtToken"]
                return BrokerAuthResponse(
                    broker=BrokerName.ANGELONE, authenticated=True,
                    session_token=jwt_token,
                    user_id=client_id,
                    message=f"Connected to Angel One as {data['data'].get('name', client_id)}",
                )
            else:
                return BrokerAuthResponse(
                    broker=BrokerName.ANGELONE, authenticated=False,
                    message=f"Angel One login failed: {data.get('message', 'Unknown error')}",
                )

        except Exception as e:
            logger.error(f"AngelOne auth failed: {e}")
            return BrokerAuthResponse(
                broker=BrokerName.ANGELONE, authenticated=False,
                message=f"Angel One auth failed: {str(e)}",
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        obj = self._get_smart_api(session_token)
        response = await asyncio.to_thread(obj.holding)
        holdings = []
        if response.get("status") and response.get("data"):
            for h in response["data"]:
                holdings.append(Holding(
                    symbol=h.get("tradingsymbol", ""),
                    quantity=h.get("quantity", 0),
                    average_price=h.get("averageprice", 0.0),
                    current_price=h.get("ltp", 0.0),
                    pnl=h.get("profitandloss", 0.0),
                    exchange=h.get("exchange", "NSE"),
                ))
        return holdings

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        obj = self._get_smart_api(session_token)
        try:
            transaction_type = "BUY" if instruction.action in (
                TradeAction.BUY, TradeAction.REBALANCE
            ) else "SELL"

            symbol_token = self.SYMBOL_TOKENS.get(instruction.symbol.upper(), "")
            if not symbol_token:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message=f"Symbol token not found for {instruction.symbol}. Add it to SYMBOL_TOKENS mapping.",
                )

            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": instruction.symbol,
                "symboltoken": symbol_token,
                "transactiontype": transaction_type,
                "exchange": instruction.exchange,
                "ordertype": "MARKET" if instruction.order_type == "MARKET" else "LIMIT",
                "producttype": "DELIVERY",
                "duration": "DAY",
                "price": str(instruction.price) if instruction.price else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(abs(instruction.quantity)),
            }
            response = await asyncio.to_thread(obj.placeOrder, order_params)

            if response:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                    order_id=str(response),
                    message="Order placed successfully on Angel One",
                )
            else:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message="Angel One order rejected",
                )
        except Exception as e:
            logger.error(f"AngelOne order failed for {instruction.symbol}: {e}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=f"Angel One order failed: {str(e)}",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        obj = self._get_smart_api(session_token)
        try:
            order_book = await asyncio.to_thread(obj.orderBook)
            if order_book.get("status") and order_book.get("data"):
                for order in order_book["data"]:
                    if order.get("orderid") == order_id:
                        is_complete = order.get("orderstatus") == "complete"
                        return OrderResult(
                            symbol=order.get("tradingsymbol", ""),
                            action=TradeAction.BUY if order.get("transactiontype") == "BUY" else TradeAction.SELL,
                            quantity=int(order.get("quantity", 0)),
                            status=OrderStatus.EXECUTED if is_complete else OrderStatus.FAILED,
                            order_id=order_id,
                            executed_price=float(order.get("averageprice", 0)),
                            message=order.get("text", ""),
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
