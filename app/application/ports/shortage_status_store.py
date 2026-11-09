"""Port: Redis shortage:{rxcui} hash."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class ShortageStatusStore(ABC):
    @abstractmethod
    async def get(self, rxcui: str) -> dict | None: ...

    @abstractmethod
    async def set(self, rxcui: str, status: dict, ttl_seconds: int | None = None) -> None: ...

