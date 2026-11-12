"""FR-15: unfollow an ingredient."""
from app.application.ports.follow_store import FollowStore


class UnfollowDrug:
    def __init__(self, follows: FollowStore) -> None:
        self.follows = follows

    async def execute(self, user_id: str, rxcui: str) -> None:
        await self.follows.unfollow(user_id, rxcui)
