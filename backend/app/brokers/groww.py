import asyncio
import logging
import random
import uuid
from typing import List

from app.brokers.base import BrokerAdapter
from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName, Holding
from app.models.portfolio import TradeInstruction, OrderResult, OrderStatus, TradeAction
from app.config import settings

logger = logging.getLogger(__name__)


class GrowwAdapter(BrokerAdapter):
    """
    Adapter for Groww.

    ⚠️  IMPORTANT: Groww does NOT offer a public trading API as of 2025.
    Unlike Zerodha/Fyers/AngelOne/Upstox/Dhan, Groww has not released a
    developer API for programmatic trading.

    This adapter uses MOCK/SIMULATED responses. It is included to:
      - Demonstrate the Adapter Pattern (easily swap in real API when available)
      - Show that the architecture supports any broker
      - Allow UI testing with Groww as a broker option

    When Groww releases a public API, replace the mock methods below with
    real API calls — zero changes needed in the engine, routers, or notifications.
    """

    name = "groww"

    MOCK_HOLDINGS = [
        Holding(symbol="BAJFINANCE", quantity=6, average_price=6800.0, current_price=7100.0, exchange="NSE"),
        Holding(symbol="MARUTI", quantity=3, average_price=10200.0, current_price=10500.0, exchange="NSE"),
        Holding(symbol="LT", quantity=10, average_price=3200.0, current_price=3350.0, exchange="NSE"),
    ]

    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        logger.warning("Groww does not have a public trading API. Using simulated auth.")
        await asyncio.sleep(0.2)
        return BrokerAuthResponse(
            broker=BrokerName.GROWW,
            authenticated=True,
            session_token=f"groww_sim_{uuid.uuid4().hex[:16]}",
            user_id="GROWW_SIM",
            message="Connected to Groww (SIMULATED — Groww has no public trading API)",
        )

    async def get_holdings(self, session_token: str) -> List[Holding]:
        logger.warning("Groww holdings are simulated. No public API available.")
        await asyncio.sleep(0.1)
        return self.MOCK_HOLDINGS

    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        logger.warning(f"Groww order for {instruction.symbol} is simulated. No public API available.")
        await asyncio.sleep(random.uniform(0.1, 0.3))

        success = random.random() < 0.9
        if success:
            executed_price = random.uniform(100, 5000)
            return OrderResult(
                symbol=instruction.symbol,
                action=instruction.action,
                quantity=abs(instruction.quantity),
                status=OrderStatus.EXECUTED,
                order_id=f"GW_SIM_{uuid.uuid4().hex[:8].upper()}",
                executed_price=round(executed_price, 2),
                message="Order executed on Groww (SIMULATED)",
            )
        else:
            return OrderResult(
                symbol=instruction.symbol,
                action=instruction.action,
                quantity=abs(instruction.quantity),
                status=OrderStatus.FAILED,
                message="Order rejected (SIMULATED — Groww has no public trading API)",
            )

    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        await asyncio.sleep(0.1)
        return OrderResult(
            symbol="UNKNOWN",
            action=TradeAction.BUY,
            quantity=0,
            status=OrderStatus.EXECUTED,
            order_id=order_id,
            message="Order status (SIMULATED — Groww has no public trading API)",
        )
