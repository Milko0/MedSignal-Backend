"""Port: RxNorm / RxClass access (cached). Returns parsed domain objects, never raw JSON."""
from abc import ABC, abstractmethod

from app.domain.entities.drug import Drug, DrugClass
from app.domain.entities.name_mapping import NameCandidate
from app.domain.entities.rx_concept import RxConcept


class DrugNormalizer(ABC):
    @abstractmethod
    async def concept(self, rxcui: str) -> RxConcept | None:
        """Product-level concept with its ingredient rxcuis (the concept itself when it is an ingredient)."""

    @abstractmethod
    async def ingredient(self, rxcui: str) -> Drug | None: ...

    @abstractmethod
    async def exact(self, name: str) -> list[str]: ...

    @abstractmethod
    async def approximate(self, term: str, max_entries: int = 5) -> list[NameCandidate]: ...

    @abstractmethod
    async def atc_classes(self, ingredient_rxcui: str) -> list[DrugClass]: ...
