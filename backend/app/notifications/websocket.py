import json
import logging
from typing import List

from fastapi import WebSocket

from app.notifications.base import Notifier
from app.models.portfolio import ExecutionSummary

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for real-time notifications."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)


# Global connection manager instance
manager = ConnectionManager()


class WebSocketNotifier(Notifier):
    """Broadcasts execution summary to all connected WebSocket clients."""

    def __init__(self, connection_manager: ConnectionManager | None = None):
        self.manager = connection_manager or manager

    async def notify(self, summary: ExecutionSummary) -> None:
        payload = {
            "event": "trade_execution_complete",
            "broker": summary.broker,
            "mode": summary.mode.value,
            "total_orders": summary.total_orders,
            "successful": summary.successful,
            "failed": summary.failed,
            "results": [
                {
                    "symbol": r.symbol,
                    "action": r.action.value,
                    "quantity": r.quantity,
                    "status": r.status.value,
                    "order_id": r.order_id,
                    "executed_price": r.executed_price,
                    "message": r.message,
                }
                for r in summary.results
            ],
            "timestamp": summary.timestamp.isoformat(),
        }

        if self.manager.active_connections:
            await self.manager.broadcast(payload)
            logger.info(
                f"WebSocket notification broadcast to "
                f"{len(self.manager.active_connections)} clients"
            )
        else:
            logger.info("No WebSocket clients connected — skipping broadcast")
