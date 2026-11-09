"""Port: Redis alert hashes with 30-day TTL plus a sorted-set index."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class AlertStore(ABC):
    @abstractmethod
    async def add(self, user_id: str, event_id: str, payload: dict) -> None: ...

    @abstractmethod
    async def list(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    async def dismiss(self, user_id: str, event_id: str) -> None: ...

    @abstractmethod
    async def dismiss_all(self, user_id: str) -> None: ...

