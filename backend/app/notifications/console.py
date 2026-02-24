import logging

from app.notifications.base import Notifier
from app.models.portfolio import ExecutionSummary, OrderStatus

logger = logging.getLogger(__name__)


class ConsoleNotifier(Notifier):
    """Logs execution summary to the console/stdout."""

    async def notify(self, summary: ExecutionSummary) -> None:
        logger.info("=" * 60)
        logger.info("TRADE EXECUTION NOTIFICATION")
        logger.info("=" * 60)
        logger.info(f"Broker:     {summary.broker}")
        logger.info(f"Mode:       {summary.mode.value}")
        logger.info(f"Total:      {summary.total_orders} orders")
        logger.info(f"Successful: {summary.successful}")
        logger.info(f"Failed:     {summary.failed}")
        logger.info("-" * 60)

        for result in summary.results:
            status_icon = "✓" if result.status == OrderStatus.EXECUTED else "✗"
            price_str = f" @ ₹{result.executed_price}" if result.executed_price else ""
            logger.info(
                f"  {status_icon} {result.action.value:10s} {result.quantity:>5d} x "
                f"{result.symbol:<15s} [{result.status.value}]{price_str}"
            )
            if result.status == OrderStatus.FAILED and result.message:
                logger.info(f"    Reason: {result.message}")

        logger.info("=" * 60)
