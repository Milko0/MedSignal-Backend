"""Port: NDC products with embedded packages."""
from abc import ABC, abstractmethod

from app.domain.entities.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def upsert_many(self, products: list[Product]) -> int: ...

    @abstractmethod
    async def get(self, product_ndc: str) -> Product | None: ...

    @abstractmethod
    async def find_by_ingredient(self, ingredient_rxcui: str, route: str | None = None,
                                 dosage_form: str | None = None) -> list[Product]: ...

    @abstractmethod
    async def product_ingredient_map(self) -> dict[str, list[str]]:
        """product NDC -> ingredient rxcuis."""
