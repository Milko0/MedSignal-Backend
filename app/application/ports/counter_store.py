"""Port: Redis live counters, set by recomputation (idempotent)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class CounterStore(ABC):
    @abstractmethod
    async def set(self, rxcui: str, reaction: str, quarter: str, value: int) -> None: ...

    @abstractmethod
    async def get(self, rxcui: str, reaction: str, quarter: str) -> int | None: ...

