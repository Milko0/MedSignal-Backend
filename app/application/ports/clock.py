"""Port: Time source (mockable)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class Clock(ABC):
    @abstractmethod
    async def now(self) -> datetime: ...

