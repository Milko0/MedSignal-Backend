"""FR-01: typo tolerant search normalised to an ingredient rxcui."""
from app.application.dtos.drugs import DrugSearchResult
from app.application.ports.ingredient_repository import IngredientRepository


class SearchDrug:
    def __init__(self, ingredients: IngredientRepository) -> None:
        self.ingredients = ingredients

    async def execute(self, query: str, limit: int = 10) -> list[DrugSearchResult]:
        found = await self.ingredients.search(query, limit)
        return [DrugSearchResult(rxcui=d.rxcui, name=d.name, brand_names=d.brand_names[:5], matched=m, score=round(s, 3))
                for d, m, s in found]
