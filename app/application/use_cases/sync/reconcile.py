"""FR-27: rebuild the live layer (shortage summaries) from the documents and fix drift."""
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.services.shortage_summary import summarize


class Reconcile:
    def __init__(self, ingredients: IngredientRepository, shortages: ShortageRepository,
                 shortage_status: ShortageStatusStore, clock) -> None:
        self.ingredients, self.shortages, self.shortage_status, self.clock = ingredients, shortages, shortage_status, clock

    async def execute(self) -> dict[str, int]:
        current = await self.shortages.current_by_package()
        ingredient_ids = {i for r in current.values() for i in r.ingredient_rxcuis}
        fixed = 0
        for rxcui in ingredient_ids:
            expected = summarize(rxcui, await self.shortages.find_by_ingredient(rxcui), self.clock.now())
            stored = await self.shortage_status.get(rxcui)
            if stored is None or (stored.worst_status, stored.packages_in_shortage, stored.packages_total) != (
                    expected.worst_status, expected.packages_in_shortage, expected.packages_total):
                await self.shortage_status.set(expected, 3600)
                fixed += 1
        return {"ingredients_checked": len(ingredient_ids), "summaries_fixed": fixed}
