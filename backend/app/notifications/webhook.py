import logging

import httpx

from app.notifications.base import Notifier
from app.models.portfolio import ExecutionSummary
from app.config import settings

logger = logging.getLogger(__name__)


class WebhookNotifier(Notifier):
    """Sends execution summary to a configured webhook URL via HTTP POST."""

    def __init__(self, url: str | None = None):
        self.url = url or settings.webhook_url

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

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.url, json=payload)
                logger.info(
                    f"Webhook notification sent to {self.url} — "
                    f"status: {response.status_code}"
                )
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
