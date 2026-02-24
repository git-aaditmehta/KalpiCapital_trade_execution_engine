import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.portfolio import ExecutionRequest, ExecutionSummary
from app.models.broker import Holding
from app.brokers.registry import get_broker_adapter
from app.engine.executor import TradeExecutor
from app.notifications.console import ConsoleNotifier
from app.notifications.webhook import WebhookNotifier
from app.notifications.websocket import WebSocketNotifier

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/holdings", response_model=List[Holding])
async def get_holdings(broker: str, session_token: str = "mock_session"):
    """
    Fetch current holdings from the broker.
    In production, session_token would be validated.
    """
    try:
        adapter = get_broker_adapter(broker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        holdings = await adapter.get_holdings(session_token)
        return holdings
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch holdings: {str(e)}",
        )

@router.get("/symbols/{broker}")
async def get_symbols(broker: str, session_token: str = "mock_session", query: str = ""):
    """
    Get available symbols for a broker with optional search query.
    """
    try:
        adapter = get_broker_adapter(broker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # For Dhan, return all available symbols
        if broker == "dhan":
            from app.brokers.dhan import DhanAdapter
            dhan_adapter = adapter
            if isinstance(dhan_adapter, DhanAdapter):
                await dhan_adapter._get_all_symbols(session_token)
                all_symbols = dhan_adapter._all_symbols
                
                # Filter by query if provided
                if query:
                    filtered = {k: v for k, v in all_symbols.items() if query.upper() in k}
                    return {"symbols": list(filtered.keys())[:50]}  # Limit to 50 results
                
                return {"symbols": list(all_symbols.keys())[:100]}  # Limit to 100 results
        
        # For other brokers, return static list
        return {"symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]}
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch symbols: {str(e)}",
        )


@router.post("/execute", response_model=ExecutionSummary)
async def execute_portfolio(request: ExecutionRequest):
    """
    Execute portfolio trades (first-time or rebalance).

    - first_time: All instructions must be BUY orders.
    - rebalance: Instructions can be BUY, SELL, or REBALANCE.
      REBALANCE actions with positive qty become BUY, negative become SELL.
    """
    print(f"🚀 EXECUTE REQUEST: {request}")
    logger.info(f"Execute request received: {request}")
    
    try:
        executor = TradeExecutor(
            broker_name=request.broker,
            session_token=request.session_token,
        )
        print(f"🚀 EXECUTOR CREATED for {request.broker}")
    except ValueError as e:
        print(f"❌ EXECUTOR ERROR: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    try:
        print(f"🚀 STARTING EXECUTION...")
        summary = await executor.execute(request)
        print(f"📊 EXECUTION SUMMARY: {summary}")
    except ValueError as e:
        print(f"❌ VALIDATION ERROR: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"❌ EXECUTION ERROR: {e}")
        logger.error(f"Execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Execution engine error: {str(e)}",
        )

    # Fire notifications on all channels
    notifiers = [ConsoleNotifier(), WebhookNotifier(), WebSocketNotifier()]
    for notifier in notifiers:
        try:
            await notifier.notify(summary)
        except Exception as e:
            logger.error(f"Notification failed ({notifier.__class__.__name__}): {e}")

    return summary
