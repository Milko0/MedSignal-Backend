"""Port: shortage list: current state per package plus our own event history."""
from abc import ABC, abstractmethod

from app.domain.entities.shortage import ShortageEvent, ShortageRecord


class ShortageRepository(ABC):
    @abstractmethod
    async def current_by_package(self) -> dict[str, ShortageRecord]: ...

    @abstractmethod
    async def replace_current(self, records: list[ShortageRecord]) -> int:
        """Stores the new current set (records that left the list are removed)."""

    @abstractmethod
    async def get(self, package_ndc: str) -> ShortageRecord | None: ...

    @abstractmethod
    async def upsert(self, record: ShortageRecord) -> None:
        """Adds or replaces one current record (admin correction, FR-24)."""

    @abstractmethod
    async def delete(self, package_ndc: str) -> bool: ...

    @abstractmethod
    async def add_events(self, events: list[ShortageEvent]) -> int: ...

    @abstractmethod
    async def find_by_ingredient(self, ingredient_rxcui: str) -> list[ShortageRecord]: ...

    @abstractmethod
    async def events_for_ingredient(self, ingredient_rxcui: str, limit: int = 100) -> list[ShortageEvent]: ...
