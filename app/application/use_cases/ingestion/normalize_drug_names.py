"""FR-29: resolve every drug name of incoming reports. Returns the resolver stats (match rate, NFR-08)."""
from app.application.services.ingredient_resolver import IngredientResolver


class NormalizeDrugNames:
    def __init__(self, resolver: IngredientResolver) -> None:
        self.resolver = resolver

    async def execute(self, names: list[str]) -> dict[str, int]:
        await self.resolver.resolve_names(names)
        return dict(self.resolver.stats)
