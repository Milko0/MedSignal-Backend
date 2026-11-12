"""Port: ingredients (the Drug hub, RxNorm TTY IN)."""
from abc import ABC, abstractmethod

from app.domain.entities.drug import Drug


class IngredientRepository(ABC):
    @abstractmethod
    async def get(self, rxcui: str) -> Drug | None: ...

    @abstractmethod
    async def get_many(self, rxcuis: list[str]) -> list[Drug]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[tuple[Drug, str, float]]:
        """Typo tolerant search over names, synonyms and brand names. Returns (drug, matched text, score 0..1)."""

    @abstractmethod
    async def list_by_class(self, class_id: str) -> list[Drug]: ...

    @abstractmethod
    async def upsert_many(self, drugs: list[Drug]) -> int: ...

    @abstractmethod
    async def count(self) -> int: ...
