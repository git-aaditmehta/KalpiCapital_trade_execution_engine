from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, portfolio, ws
from app.api import broker_routes
from app.notifications.websocket import manager as ws_manager

app = FastAPI(
    title="Kalpi Capital - Portfolio Trade Execution Engine",
    description="End-to-end engine for systematic portfolio execution across Indian brokers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Broker Authentication"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio Execution"])
app.include_router(ws.router, tags=["WebSocket Notifications"])
app.include_router(broker_routes.router, tags=["Broker Operations"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Kalpi Capital Trade Execution Engine",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.app_env}


@app.post("/webhook/mock", tags=["Webhook"])
async def mock_webhook_receiver(payload: dict):
    """Mock webhook endpoint to receive and log execution notifications."""
    print(f"[WEBHOOK RECEIVED] {payload}")
    return {"status": "received", "payload": payload}
