"""MongoDB -> Redis event sync. Watches `signals` and `shortages`, hands each change to ProjectChangeEvent and saves
the resume token in `sync_checkpoints` (every 200 changes and whenever the stream goes quiet), so a restart resumes
where it stopped. Replays are harmless: the projection overwrites values and alert ids are deterministic.

Change streams need a replica set (the compose cluster and the Virtual Lab are). On a standalone mongod the worker
falls back to the periodic Reconcile (FR-27).
"""
import logging

from pymongo.errors import OperationFailure

from app.application.use_cases.sync.project_change_event import ProjectChangeEvent
from app.domain.entities.signal import SafetySignal
from app.infrastructure.mongodb.documents import from_doc
from app.infrastructure.sync.checkpoint_store import CheckpointStore

log = logging.getLogger("medsignal.sync")

WATCHED = ["signals", "shortages"]
SAVE_EVERY = 200
CHECKPOINT = "redis_projector"


async def supports_change_streams(client) -> bool:
    hello = await client.admin.command("hello")
    return bool(hello.get("setName")) or hello.get("msg") == "isdbgrid"


class ChangeStreamProjector:
    def __init__(self, db, project: ProjectChangeEvent, checkpoints: CheckpointStore) -> None:
        self.db, self.project, self.checkpoints = db, project, checkpoints
        self.processed = 0

    async def handle(self, change: dict) -> None:
        doc = change.get("fullDocument")
        if doc is None:                       # deletes carry no document; Reconcile fixes what they leave behind
            return
        collection = change["ns"]["coll"]
        if collection == "signals":
            await self.project.signal_changed(from_doc(SafetySignal, doc, "signal_id"))
        elif collection == "shortages":
            await self.project.shortage_changed(doc.get("ingredient_rxcuis", []))

    async def run(self) -> None:
        pipeline = [{"$match": {"ns.coll": {"$in": WATCHED},
                                "operationType": {"$in": ["insert", "update", "replace"]}}}]
        token = await self.checkpoints.load(CHECKPOINT)
        try:
            stream = await self.db.watch(pipeline, full_document="updateLookup", resume_after=token)
        except OperationFailure as exc:          # token too old for the oplog: start from now, Reconcile covers the gap
            log.warning("Resume token rejected (%s); starting from the current time", exc)
            await self.checkpoints.clear(CHECKPOINT)
            stream = await self.db.watch(pipeline, full_document="updateLookup")
        log.info("Change-stream projector watching %s (resumed: %s)", WATCHED, token is not None)
        unsaved = 0
        async with stream:
            while stream.alive:
                change = await stream.try_next()
                if change is None:              # quiet: persist progress
                    if unsaved:
                        await self.checkpoints.save(CHECKPOINT, stream.resume_token)
                        unsaved = 0
                    continue
                await self.handle(change)
                self.processed += 1
                unsaved += 1
                if unsaved >= SAVE_EVERY:
                    await self.checkpoints.save(CHECKPOINT, stream.resume_token)
                    unsaved = 0
