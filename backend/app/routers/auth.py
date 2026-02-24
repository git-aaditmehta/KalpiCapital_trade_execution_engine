from fastapi import APIRouter, HTTPException

from app.models.broker import BrokerCredentials, BrokerAuthResponse, BrokerName
from app.brokers.registry import BrokerRegistry, get_broker_adapter

router = APIRouter()


@router.post("/connect", response_model=BrokerAuthResponse)
async def connect_broker(credentials: BrokerCredentials):
    """
    Authenticate with a stock broker.
    Returns a session token on success.
    """
    try:
        adapter = get_broker_adapter(credentials.broker.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        auth_response = await adapter.authenticate(credentials)
        return auth_response
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Broker authentication failed: {str(e)}",
        )


@router.get("/brokers", response_model=list[str])
async def list_brokers():
    """List all supported brokers."""
    return BrokerRegistry.list_brokers()
