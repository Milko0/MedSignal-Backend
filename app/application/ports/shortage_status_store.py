"""Port: key-value: live shortage summary per ingredient."""
from abc import ABC, abstractmethod

from app.domain.entities.shortage import ShortageSummary


class ShortageStatusStore(ABC):
    @abstractmethod
    async def get(self, ingredient_rxcui: str) -> ShortageSummary | None: ...

    @abstractmethod
    async def set(self, summary: ShortageSummary, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    async def delete(self, ingredient_rxcui: str) -> None: ...
