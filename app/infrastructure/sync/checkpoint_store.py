"""Stores the change-stream resume token in `sync_checkpoints` so the worker restarts where it stopped."""
from datetime import UTC, datetime


class CheckpointStore:
    def __init__(self, db) -> None:
        self.col = db["sync_checkpoints"]

    async def load(self, name: str) -> dict | None:
        doc = await self.col.find_one({"_id": name})
        return doc["token"] if doc else None

    async def save(self, name: str, token: dict | None) -> None:
        if token is not None:
            await self.col.replace_one({"_id": name}, {"_id": name, "token": token, "updated_at": datetime.now(UTC)},
                                       upsert=True)

    async def clear(self, name: str) -> None:
        await self.col.delete_one({"_id": name})
