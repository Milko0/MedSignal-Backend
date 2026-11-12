"""Port: DailyMed / openFDA labels (one document per set id)."""
from abc import ABC, abstractmethod

from app.domain.entities.enums import ProductType
from app.domain.entities.label import DrugLabel


class LabelRepository(ABC):
    @abstractmethod
    async def upsert_many(self, labels: list[DrugLabel]) -> int: ...

    @abstractmethod
    async def get(self, set_id: str) -> DrugLabel | None: ...

    @abstractmethod
    async def find_by_ingredient(self, ingredient_rxcui: str, product_type: ProductType | None = None) -> list[DrugLabel]: ...

    @abstractmethod
    async def count(self) -> int: ...
