"""Port: Recalls matched to drugs."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class RecallRepository(ABC):
    @abstractmethod
    async def upsert_many(self, recalls: list[dict]) -> int: ...

    @abstractmethod
    async def counts_by_class(self, rxcui: str) -> dict[str, int]: ...

