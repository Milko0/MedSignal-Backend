"""Live shortage summary of an ingredient, cache-aside: the key-value store first, the documents on a miss."""
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.entities.shortage import ShortageSummary
from app.domain.services.shortage_summary import summarize

CACHE_TTL_SECONDS = 3600


class ShortageStatusReader:
    def __init__(self, shortage_status: ShortageStatusStore, shortages: ShortageRepository, clock) -> None:
        self.shortage_status, self.shortages, self.clock = shortage_status, shortages, clock

    async def summary(self, ingredient_rxcui: str) -> ShortageSummary:
        cached = await self.shortage_status.get(ingredient_rxcui)
        if cached is not None:
            return cached
        summary = summarize(ingredient_rxcui, await self.shortages.find_by_ingredient(ingredient_rxcui),
                            self.clock.now())
        await self.shortage_status.set(summary, CACHE_TTL_SECONDS)
        return summary

    async def worst_status(self, ingredient_rxcuis) -> dict[str, str | None]:
        """ingredient -> CURRENT | TO_BE_DISCONTINUED | RESOLVED | None (never listed)."""
        out = {}
        for rxcui in dict.fromkeys(ingredient_rxcuis):
            s = await self.summary(rxcui)
            out[rxcui] = s.worst_status.value if s.worst_status else None
        return out
