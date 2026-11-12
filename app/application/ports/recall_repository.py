"""Port: recalls and their explicit, auditable links to ingredients."""
from abc import ABC, abstractmethod

from app.domain.entities.recall import Recall


class RecallRepository(ABC):
    @abstractmethod
    async def upsert_many(self, recalls: list[Recall]) -> int: ...

    @abstractmethod
    async def all(self) -> list[Recall]: ...

    @abstractmethod
    async def find_by_ingredient(self, ingredient_rxcui: str, accepted_only: bool = True) -> list[Recall]: ...

    @abstractmethod
    async def linked_share(self) -> float:
        """Share of recalls with an ACCEPTED link (shown next to every recall count)."""
