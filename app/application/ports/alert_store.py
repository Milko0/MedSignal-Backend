"""Port: key-value: alerts with a 30-day TTL."""
from abc import ABC, abstractmethod

from app.domain.entities.alert import Alert


class AlertStore(ABC):
    @abstractmethod
    async def add(self, alert: Alert, ttl_seconds: int) -> bool:
        """Creates the alert only if its id does not exist (idempotent). Returns True if created."""

    @abstractmethod
    async def list(self, user_id: str, limit: int = 50) -> list[Alert]: ...

    @abstractmethod
    async def dismiss(self, user_id: str, alert_id: str) -> bool: ...

    @abstractmethod
    async def dismiss_all(self, user_id: str) -> int: ...
