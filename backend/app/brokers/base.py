from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from app.models.broker import BrokerCredentials, BrokerAuthResponse, Holding
from app.models.portfolio import TradeInstruction, OrderResult


class BrokerAdapter(ABC):
    """
    Abstract base class for all broker integrations.
    Every broker adapter must implement these methods.
    Adding a new broker = subclass this + register in BrokerRegistry.
    """

    name: str = "base"

    @abstractmethod
    async def authenticate(self, credentials: BrokerCredentials) -> BrokerAuthResponse:
        """Authenticate with the broker and return a session token."""
        ...

    @abstractmethod
    async def get_holdings(self, session_token: str) -> List[Holding]:
        """Fetch the user's current portfolio holdings."""
        ...

    @abstractmethod
    async def place_order(self, session_token: str, instruction: TradeInstruction) -> OrderResult:
        """Place a single order (BUY/SELL) with the broker."""
        ...

    @abstractmethod
    async def get_order_status(self, session_token: str, order_id: str) -> OrderResult:
        """Check the status of a previously placed order."""
        ...

    async def place_orders(self, session_token: str, instructions: List[TradeInstruction]) -> List[OrderResult]:
        """Place multiple orders sequentially. Override for batch/parallel support."""
        results = []
        for instruction in instructions:
            result = await self.place_order(session_token, instruction)
            results.append(result)
        return results
