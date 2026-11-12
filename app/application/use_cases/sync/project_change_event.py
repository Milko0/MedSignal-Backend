"""Event sync (teammates, phase 5): apply one MongoDB change event to Redis idempotently.

Contract: overwrite values from MongoDB (never increment), deterministic alert ids, resume token in sync_checkpoints.
"""


class ProjectChangeEvent:
    async def execute(self, event: dict) -> None:
        raise NotImplementedError("Written with the MongoDB change-stream adapter")
