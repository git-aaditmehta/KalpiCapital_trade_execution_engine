from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class BrokerName(str, Enum):
    ZERODHA = "zerodha"
    FYERS = "fyers"
    ANGELONE = "angelone"
    GROWW = "groww"
    UPSTOX = "upstox"
    DHAN = "dhan"


class BrokerCredentials(BaseModel):
    broker: BrokerName
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    client_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Broker-specific fields")


class BrokerAuthResponse(BaseModel):
    broker: BrokerName
    authenticated: bool
    session_token: Optional[str] = None
    user_id: Optional[str] = None
    login_url: Optional[str] = None
    message: str


class Holding(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: Optional[float] = None
    pnl: Optional[float] = None
    exchange: str = "NSE"
