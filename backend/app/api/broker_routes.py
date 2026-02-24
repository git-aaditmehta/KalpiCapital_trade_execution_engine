import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from app.services.broker_service import broker_service
from app.models.broker import BrokerAuthResponse, Holding
from app.models.portfolio import TradeInstruction, OrderResult, ExecutionSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broker", tags=["broker"])


class ZerodhaCallbackRequest(BaseModel):
    request_token: str


class ExecuteTradesRequest(BaseModel):
    broker: str
    access_token: str
    trades: List[TradeInstruction]


class OrderStatusRequest(BaseModel):
    broker: str
    access_token: str
    order_id: str


@router.get("/zerodha/login", response_model=BrokerAuthResponse)
async def zerodha_login():
    """
    Initiate Zerodha OAuth login flow.
    Returns login URL for user to authenticate.
    """
    try:
        response = await broker_service.connect_zerodha()
        return response
    except Exception as e:
        logger.error(f"Zerodha login endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zerodha/callback", response_model=BrokerAuthResponse)
async def zerodha_callback(request: ZerodhaCallbackRequest):
    """
    Handle Zerodha OAuth callback.
    Exchange request_token for access_token.
    """
    if not request.request_token:
        raise HTTPException(status_code=400, detail="Missing request_token")
    
    try:
        response = await broker_service.zerodha_callback(request.request_token)
        return response
    except Exception as e:
        logger.error(f"Zerodha callback endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported")
async def list_supported_brokers():
    """
    Get list of all supported brokers.
    """
    try:
        brokers = broker_service.list_supported_brokers()
        return {"brokers": brokers}
    except Exception as e:
        logger.error(f"List brokers endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{broker_name}/holdings", response_model=List[Holding])
async def get_holdings(broker_name: str, access_token: str = Query(...)):
    """
    Fetch holdings for a specific broker.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access_token")
    
    try:
        holdings = await broker_service.get_holdings(broker_name, access_token)
        return holdings
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Holdings endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{broker_name}/order", response_model=OrderResult)
async def place_order(broker_name: str, access_token: str = Query(...), instruction: TradeInstruction = ...):
    """
    Place a single order for a specific broker.
    """
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access_token")
    
    try:
        result = await broker_service.place_order(broker_name, access_token, instruction)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Place order endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{broker_name}/execute", response_model=ExecutionSummary)
async def execute_trades(request: ExecuteTradesRequest):
    """
    Execute multiple trades using the execution engine.
    """
    if not request.access_token:
        raise HTTPException(status_code=400, detail="Missing access_token")
    
    try:
        summary = await broker_service.execute_trades(
            request.broker, 
            request.access_token, 
            request.trades
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Execute trades endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{broker_name}/order-status", response_model=OrderResult)
async def get_order_status(broker_name: str, request: OrderStatusRequest):
    """
    Get order status for a specific broker.
    """
    if not request.access_token:
        raise HTTPException(status_code=400, detail="Missing access_token")
    
    if not request.order_id:
        raise HTTPException(status_code=400, detail="Missing order_id")
    
    try:
        result = await broker_service.get_order_status(
            broker_name, 
            request.access_token, 
            request.order_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Order status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{broker_name}/authenticate")
async def authenticate_broker(broker_name: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
    """
    Authenticate with a broker using API credentials.
    For testing purposes or when using pre-generated tokens.
    """
    try:
        from app.models.broker import BrokerCredentials
        from app.brokers.registry import get_broker_adapter
        
        adapter = get_broker_adapter(broker_name)
        credentials = BrokerCredentials(
            broker=broker_name,
            api_key=api_key,
            api_secret=api_secret
        )
        response = await adapter.authenticate(credentials)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Authenticate endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
