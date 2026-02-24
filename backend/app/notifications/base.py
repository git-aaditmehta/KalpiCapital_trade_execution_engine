from abc import ABC, abstractmethod

from app.models.portfolio import ExecutionSummary


class Notifier(ABC):
    """
    Abstract base class for notification channels.
    Extend this to add new notification methods (email, SMS, Slack, etc.).
    """

    @abstractmethod
    async def notify(self, summary: ExecutionSummary) -> None:
        """Send an execution summary notification."""
        ...
