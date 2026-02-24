import asyncio
import logging
from typing import List

import httpx

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)

UPSTOX_BASE = "https://api.upstox.com/v2"


class UpstoxAdapter(BrokerAdapter):
    """
    Real adapter for Upstox using the Upstox REST API v2.
    API docs: https://upstox.com/developer/api-documentation/
    Portal: https://account.upstox.com/developer/apps
    Auth flow:
      1. Create app on Upstox Developer portal → get api_key & api_secret & redirect_uri
      2. Redirect user to Upstox login → user grants access → redirected with auth_code
      3. Exchange auth_code for access_token
      4. Store access_token in .env (valid for 1 trading day)
    Upstox uses instrument_key format: "NSE_EQ|INE002A01018" (exchange|ISIN).
    For simplicity, we use the /order endpoint with tradingsymbol.
    """

    name = "upstox"

    # Common symbol → instrument_key mapping for Upstox (NSE equity)
    # Full list: https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz
    INSTRUMENT_KEYS = {
        "RELIANCE": "NSE_EQ|INE002A01018", "TCS": "NSE_EQ|INE467B01029",
        "INFY": "NSE_EQ|INE009A01021", "HDFCBANK": "NSE_EQ|INE040A01034",
        "ICICIBANK": "NSE_EQ|INE090A01021", "ITC": "NSE_EQ|INE154A01025",
        "SBIN": "NSE_EQ|INE062A01020", "TATAMOTORS": "NSE_EQ|INE155A01022",
        "WIPRO": "NSE_EQ|INE075A01022", "BHARTIARTL": "NSE_EQ|INE397D01024",
        "AXISBANK": "NSE_EQ|INE238A01034", "SUNPHARMA": "NSE_EQ|INE044A01036",
        "HCLTECH": "NSE_EQ|INE860A01027", "KOTAKBANK": "NSE_EQ|INE237A01028",
        "LT": "NSE_EQ|INE018A01030", "MARUTI": "NSE_EQ|INE585B01010",
        "BAJFINANCE": "NSE_EQ|INE296A01024", "TITAN": "NSE_EQ|INE280A01028",
        "TATASTEEL": "NSE_EQ|INE081A01020", "NTPC": "NSE_EQ|INE733E01010",
        "ONGC": "NSE_EQ|INE213A01029", "COALINDIA": "NSE_EQ|INE522F01014",
        "ADANIENT": "NSE_EQ|INE423A01024", "TECHM": "NSE_EQ|INE669C01036",
        "NHPC": "NSE_EQ|INE848E01016", "BPCL": "NSE_EQ|INE541A01028",
        "JSWSTEEL": "NSE_EQ|INE019A01038", "HINDALCO": "NSE_EQ|INE038A01020",
    }

    def _headers(self, access_token: str) -> dict:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        try:
            api_key = credentials.api_key or settings.upstox_api_key
            api_secret = credentials.api_secret or settings.upstox_api_secret

            if not api_key:
                return BrokerAuthResponse(
                    broker=BrokerName.UPSTOX, authenticated=False,
                    message="Missing UPSTOX_API_KEY. Set it in .env or pass via request.",
                )

            # If access_token already available, validate via profile
            access_token = credentials.access_token or settings.upstox_access_token
            if access_token:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"{UPSTOX_BASE}/user/profile", headers=self._headers(access_token)
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        return BrokerAuthResponse(
                            broker=BrokerName.UPSTOX, authenticated=True,
                            session_token=access_token,
                            user_id=data.get("user_id", ""),
                            message=f"Connected to Upstox as {data.get('user_name', 'User')}",
                        )
                    else:
                        return BrokerAuthResponse(
                            broker=BrokerName.UPSTOX, authenticated=False,
                            message=f"Upstox token invalid: {resp.text}",
                        )

            # If auth_code provided, exchange for access_token
            auth_code = credentials.extra.get("auth_code") if credentials.extra else None
            if auth_code and api_secret:
                redirect_uri = settings.upstox_redirect_uri or "http://localhost:3000/callback"
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{UPSTOX_BASE}/login/authorization/token",
                        data={
                            "code": auth_code,
                            "client_id": api_key,
                            "client_secret": api_secret,
                            "redirect_uri": redirect_uri,
                            "grant_type": "authorization_code",
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
                    if resp.status_code == 200:
                        token_data = resp.json()
                        return BrokerAuthResponse(
                            broker=BrokerName.UPSTOX, authenticated=True,
                            session_token=token_data.get("access_token", ""),
                            user_id=token_data.get("user_id", ""),
                            message="Connected to Upstox successfully",
                        )
                    return BrokerAuthResponse(
                        broker=BrokerName.UPSTOX, authenticated=False,
                        message=f"Token exchange failed: {resp.text}",
                    )

            return BrokerAuthResponse(
                broker=BrokerName.UPSTOX, authenticated=False,
                message="Missing UPSTOX_ACCESS_TOKEN. Generate one from the Upstox Developer portal.",
            )

        except Exception as e:
            logger.error(f"Upstox auth failed: {e}")
            return BrokerAuthResponse(
                broker=BrokerName.UPSTOX, authenticated=False,
                message=f"Upstox auth failed: {str(e)}",
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UPSTOX_BASE}/portfolio/long-term-holdings",
                headers=self._headers(session_token),
            )
            holdings = []
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for h in data:
                    holdings.append(Holding(
                        symbol=h.get("tradingsymbol", ""),
                        quantity=h.get("quantity", 0),
                        average_price=h.get("average_price", 0.0),
                        current_price=h.get("last_price", 0.0),
                        pnl=h.get("pnl", 0.0),
                        exchange=h.get("exchange", "NSE"),
                    ))
            return holdings

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        try:
            instrument_key = self.INSTRUMENT_KEYS.get(instruction.symbol.upper(), "")
            if not instrument_key:
                return OrderResult(
                    symbol=instruction.symbol, action=instruction.action,
                    quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                    message=f"Instrument key not found for {instruction.symbol}. Add it to INSTRUMENT_KEYS mapping.",
                )

            transaction_type = "BUY" if instruction.action in (
                TradeAction.BUY, TradeAction.REBALANCE
            ) else "SELL"

            order_data = {
                "quantity": abs(instruction.quantity),
                "product": "D",  # D=Delivery
                "validity": "DAY",
                "price": instruction.price or 0,
                "tag": "kalpi",
                "instrument_token": instrument_key,
                "order_type": "MARKET" if instruction.order_type == "MARKET" else "LIMIT",
                "transaction_type": transaction_type,
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{UPSTOX_BASE}/order/place",
                    json=order_data,
                    headers=self._headers(session_token),
                )

                if resp.status_code == 200:
                    result = resp.json().get("data", {})
                    return OrderResult(
                        symbol=instruction.symbol, action=instruction.action,
                        quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                        order_id=result.get("order_id", ""),
                        message="Order placed successfully on Upstox",
                    )
                else:
                    error_msg = resp.json().get("errors", [{}])[0].get("message", resp.text) if resp.text else "Unknown error"
                    return OrderResult(
                        symbol=instruction.symbol, action=instruction.action,
                        quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                        message=f"Upstox order rejected: {error_msg}",
                    )
        except Exception as e:
            logger.error(f"Upstox order failed for {instruction.symbol}: {e}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=f"Upstox order failed: {str(e)}",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{UPSTOX_BASE}/order/details",
                    params={"order_id": order_id},
                    headers=self._headers(session_token),
                )
                if resp.status_code == 200:
                    order = resp.json().get("data", {})
                    is_complete = order.get("status") == "complete"
                    return OrderResult(
                        symbol=order.get("tradingsymbol", ""),
                        action=TradeAction.BUY if order.get("transaction_type") == "BUY" else TradeAction.SELL,
                        quantity=order.get("quantity", 0),
                        status=OrderStatus.EXECUTED if is_complete else OrderStatus.FAILED,
                        order_id=order_id,
                        executed_price=order.get("average_price"),
                        message=order.get("status_message", ""),
                    )
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message="Failed to fetch order details from Upstox",
            )
        except Exception as e:
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message=f"Failed to fetch order status: {str(e)}",
            )
