"""Port: non-specific reaction terms excluded from signals and label gaps (FR-26)."""
from abc import ABC, abstractmethod

from app.domain.entities.excluded_term import ExcludedTerm


class ExcludedTermRepository(ABC):
    @abstractmethod
    async def list(self) -> list[ExcludedTerm]: ...

    @abstractmethod
    async def add(self, term: ExcludedTerm) -> None: ...

    @abstractmethod
    async def remove(self, term: str) -> bool: ...

    async def as_set(self) -> set[str]:
        return {t.term for t in await self.list()}
