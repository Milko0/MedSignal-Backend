"""FR-15: follow an ingredient."""
from app.application.ports.follow_store import FollowStore
from app.application.ports.ingredient_repository import IngredientRepository
from app.domain.exceptions import NotFoundError


class FollowDrug:
    def __init__(self, follows: FollowStore, ingredients: IngredientRepository) -> None:
        self.follows, self.ingredients = follows, ingredients

    async def execute(self, user_id: str, rxcui: str) -> None:
        if await self.ingredients.get(rxcui) is None:
            raise NotFoundError(f"Unknown ingredient {rxcui}")
        await self.follows.follow(user_id, rxcui)
