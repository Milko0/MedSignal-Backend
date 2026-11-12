"""FR-16: medicine cabinet with the live shortage state of each followed ingredient."""
from app.application.dtos.cabinet import FollowedDrug
from app.application.ports.follow_store import FollowStore
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.services.shortage_summary import summarize


class ListFollowed:
    def __init__(self, follows: FollowStore, ingredients: IngredientRepository, shortage_status: ShortageStatusStore,
                 shortages: ShortageRepository, clock) -> None:
        self.follows, self.ingredients, self.shortage_status = follows, ingredients, shortage_status
        self.shortages, self.clock = shortages, clock

    async def execute(self, user_id: str) -> list[FollowedDrug]:
        out = []
        for drug in await self.ingredients.get_many(sorted(await self.follows.list_followed(user_id))):
            summary = await self.shortage_status.get(drug.rxcui)
            if summary is None:  # cache-aside
                summary = summarize(drug.rxcui, await self.shortages.find_by_ingredient(drug.rxcui), self.clock.now())
                await self.shortage_status.set(summary, 3600)
            out.append(FollowedDrug(rxcui=drug.rxcui, name=drug.name,
                                    shortage_status=summary.worst_status.value if summary.worst_status else None,
                                    packages_in_shortage=summary.packages_in_shortage))
        return out
