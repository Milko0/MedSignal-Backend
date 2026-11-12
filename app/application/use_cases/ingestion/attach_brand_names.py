"""Fills Drug.brand_names from the NDC products, so the search (FR-01) also finds "Ozempic" or "Advil"."""
from collections.abc import Iterable

from app.application.ports.ingredient_repository import IngredientRepository
from app.domain.entities.product import Product
from app.domain.services.brand_names import brand_names_by_ingredient


class AttachBrandNames:
    def __init__(self, ingredients: IngredientRepository) -> None:
        self.ingredients = ingredients

    async def execute(self, products: Iterable[Product]) -> int:
        """Returns how many ingredients got brand names. Idempotent: brands are replaced, never appended."""
        brands = brand_names_by_ingredient(products)
        drugs = await self.ingredients.get_many(sorted(brands))
        changed = [d.model_copy(update={"brand_names": brands[d.rxcui]}) for d in drugs
                   if d.brand_names != brands[d.rxcui]]
        if changed:
            await self.ingredients.upsert_many(changed)
        return len(changed)
