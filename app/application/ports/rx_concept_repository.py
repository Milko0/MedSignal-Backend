"""Port: product-level RxNorm concepts and their ingredients (cache of RxNav answers)."""
from abc import ABC, abstractmethod

from app.domain.entities.rx_concept import RxConcept


class RxConceptRepository(ABC):
    @abstractmethod
    async def get_many(self, rxcuis: list[str]) -> dict[str, RxConcept]: ...

    @abstractmethod
    async def upsert_many(self, concepts: list[RxConcept]) -> int: ...

    @abstractmethod
    async def all_ingredient_map(self) -> dict[str, list[str]]:
        """product rxcui -> ingredient rxcuis for every cached concept."""
