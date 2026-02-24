import asyncio
import logging
from typing import List

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)


class ZerodhaAdapter(BrokerAdapter):
    """
    Real adapter for Zerodha using the KiteConnect Python SDK.
    API docs: https://kite.trade/docs/connect/v3/
    Portal: https://developers.kite.trade
    Auth flow:
      1. Create app on Kite Developer portal → get api_key & api_secret
      2. Redirect user to Kite login URL → user logs in → redirected back with request_token
      3. Exchange request_token for access_token using api_secret
      4. Store access_token in .env (valid for 1 trading day)
    """

    name = "zerodha"

    def _get_kite(self, access_token: str = None):
        from kiteconnect import KiteConnect
        api_key = settings.zerodha_api_key
        kite = KiteConnect(api_key=api_key)
        token = access_token or settings.zerodha_access_token
        if token:
            kite.set_access_token(token)
        return kite

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        logger.info("🔐 Starting Zerodha authentication")
        
        try:
            api_key = credentials.api_key or settings.zerodha_api_key
            api_secret = credentials.api_secret or settings.zerodha_api_secret

            if not api_key:
                logger.error("❌ Missing ZERODHA_API_KEY")
                return BrokerAuthResponse(
                    broker=BrokerName.ZERODHA, authenticated=False,
                    message="Missing ZERODHA_API_KEY. Set it in .env or pass via request.",
                )

            from kiteconnect import KiteConnect
            kite = KiteConnect(api_key=api_key)

            # If access_token is already available (pre-generated), validate it
            access_token = credentials.access_token or settings.zerodha_access_token
            if access_token:
                logger.info("🔑 Validating existing access token")
                try:
                    kite.set_access_token(access_token)
                    profile = await asyncio.to_thread(kite.profile)
                    logger.info(f"✅ Successfully authenticated as {profile.get('user_name', 'User')}")
                    return BrokerAuthResponse(
                        broker=BrokerName.ZERODHA, authenticated=True,
                        session_token=access_token,
                        user_id=profile.get("user_id", ""),
                        message=f"Connected to Zerodha as {profile.get('user_name', 'User')}",
                    )
                except Exception as e:
                    logger.error(f"❌ Invalid access token: {e}")
                    # Fall through to generate new login URL

            # If request_token is provided (from OAuth redirect), exchange for access_token
            request_token = credentials.extra.get("request_token") if credentials.extra else None
            if request_token and api_secret:
                logger.info(f"🔄 Exchanging request_token for access_token")
                try:
                    data = await asyncio.to_thread(kite.generate_session, request_token, api_secret=api_secret)
                    logger.info(f"✅ Token exchange successful for user: {data.get('user_name', 'Unknown')}")
                    return BrokerAuthResponse(
                        broker=BrokerName.ZERODHA, authenticated=True,
                        session_token=data["access_token"],
                        user_id=data.get("user_id", ""),
                        message=f"Connected to Zerodha as {data.get('user_name', 'User')}",
                    )
                except Exception as e:
                    logger.error(f"❌ Token exchange failed: {e}")
                    return BrokerAuthResponse(
                        broker=BrokerName.ZERODHA, authenticated=False,
                        message=f"Failed to exchange request_token: {str(e)}",
                    )

            # Return login URL for OAuth flow
            login_url = kite.login_url()
            logger.info(f"🔗 Generated Zerodha login URL: {login_url}")
            return BrokerAuthResponse(
                broker=BrokerName.ZERODHA, authenticated=False,
                login_url=login_url,
                message="Please login via Kite to continue",
            )

        except Exception as e:
            logger.error(f"❌ Zerodha authentication failed: {e}")
            return BrokerAuthResponse(
                broker=BrokerName.ZERODHA, authenticated=False,
                message=f"Zerodha auth failed: {str(e)}",
            )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        logger.info("📊 Fetching Zerodha holdings")
        try:
            kite = self._get_kite(session_token)
            raw_holdings = await asyncio.to_thread(kite.holdings)
            holdings = []
            for h in raw_holdings:
                holdings.append(Holding(
                    symbol=h.get("tradingsymbol", ""),
                    quantity=h.get("quantity", 0),
                    average_price=h.get("average_price", 0.0),
                    current_price=h.get("last_price", 0.0),
                    pnl=h.get("pnl", 0.0),
                    exchange=h.get("exchange", "NSE"),
                ))
            logger.info(f"✅ Retrieved {len(holdings)} holdings from Zerodha")
            return holdings
        except Exception as e:
            logger.error(f"❌ Failed to fetch Zerodha holdings: {e}")
            raise

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        logger.info(f"📈 Placing Zerodha order: {instruction.action} {instruction.quantity} {instruction.symbol}")
        kite = self._get_kite(session_token)
        try:
            from kiteconnect import KiteConnect
            transaction_type = kite.TRANSACTION_TYPE_BUY if instruction.action in (
                TradeAction.BUY, TradeAction.REBALANCE
            ) else kite.TRANSACTION_TYPE_SELL

            order_id = await asyncio.to_thread(
                kite.place_order,
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_NSE if instruction.exchange == "NSE" else kite.EXCHANGE_BSE,
                tradingsymbol=instruction.symbol,
                transaction_type=transaction_type,
                quantity=abs(instruction.quantity),
                product=kite.PRODUCT_CNC,
                order_type=kite.ORDER_TYPE_MARKET if instruction.order_type == "MARKET" else kite.ORDER_TYPE_LIMIT,
                price=instruction.price if instruction.order_type == "LIMIT" else None,
            )

            logger.info(f"✅ Zerodha order placed successfully: {order_id}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.EXECUTED,
                order_id=str(order_id),
                message="Order placed successfully on Zerodha",
            )
        except Exception as e:
            logger.error(f"❌ Zerodha order failed for {instruction.symbol}: {e}")
            return OrderResult(
                symbol=instruction.symbol, action=instruction.action,
                quantity=abs(instruction.quantity), status=OrderStatus.FAILED,
                message=f"Zerodha order failed: {str(e)}",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        kite = self._get_kite(session_token)
        try:
            orders = await asyncio.to_thread(kite.order_history, order_id)
            latest = orders[-1] if orders else {}
            status = OrderStatus.EXECUTED if latest.get("status") == "COMPLETE" else OrderStatus.FAILED
            return OrderResult(
                symbol=latest.get("tradingsymbol", ""),
                action=TradeAction.BUY if latest.get("transaction_type") == "BUY" else TradeAction.SELL,
                quantity=latest.get("quantity", 0),
                status=status,
                order_id=order_id,
                executed_price=latest.get("average_price"),
                message=latest.get("status_message", ""),
            )
        except Exception as e:
            return OrderResult(
                symbol="", action=TradeAction.BUY, quantity=0,
                status=OrderStatus.FAILED, order_id=order_id,
                message=f"Failed to fetch order status: {str(e)}",
            )
