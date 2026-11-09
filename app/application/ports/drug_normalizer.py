"""Port: Drug name to RxCUI (RxNorm)."""
from abc import ABC, abstractmethod
from datetime import datetime  # noqa: F401
from typing import AsyncIterator  # noqa: F401


class DrugNormalizer(ABC):
    @abstractmethod
    async def to_rxcui(self, name: str) -> str | None: ...

    @abstractmethod
    async def approximate(self, name: str, limit: int = 3) -> list[dict]: ...

