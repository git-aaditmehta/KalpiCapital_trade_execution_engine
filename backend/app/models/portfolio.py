from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    REBALANCE = "REBALANCE"


class ExecutionMode(str, Enum):
    FIRST_TIME = "first_time"
    REBALANCE = "rebalance"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"


class TradeInstruction(BaseModel):
    action: TradeAction
    symbol: str = Field(..., min_length=1, description="NSE/BSE stock symbol")
    quantity: int = Field(..., description="Positive for BUY, negative for SELL in REBALANCE mode")
    exchange: str = Field(default="NSE", description="Exchange: NSE or BSE")
    order_type: str = Field(default="MARKET", description="Order type: MARKET or LIMIT")
    price: Optional[float] = Field(default=None, description="Limit price (required for LIMIT orders)")


class ExecutionRequest(BaseModel):
    broker: str = Field(..., description="Broker name (e.g., zerodha, fyers, angelone, groww, upstox, dhan)")
    mode: ExecutionMode
    instructions: List[TradeInstruction] = Field(..., min_length=1)
    session_token: Optional[str] = Field(default=None, description="Broker session/access token")


class OrderResult(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    status: OrderStatus
    order_id: Optional[str] = None
    executed_price: Optional[float] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionSummary(BaseModel):
    broker: str
    mode: ExecutionMode
    total_orders: int
    successful: int
    failed: int
    results: List[OrderResult]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
