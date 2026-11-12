from app.application.ports.shortage_repository import ShortageRepository
from app.domain.entities.shortage import ShortageEvent, ShortageRecord
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc


class MongoShortageRepository(ShortageRepository):
    """`shortages`: CURRENT state per package (`_id` = package_ndc). `shortage_events`: our own append-only history
    of every change seen by the daily poll (generated ids)."""

    def __init__(self, db) -> None:
        self.col = db["shortages"]
        self.events = db["shortage_events"]

    def _load(self, doc):
        return from_doc(ShortageRecord, doc, "package_ndc")

    async def current_by_package(self):
        return {d["_id"]: self._load(d) async for d in self.col.find({})}

    async def replace_current(self, records):
        ids = [r.package_ndc for r in records]
        await replace_many(self.col, [to_doc(r, "package_ndc") for r in records])
        await self.col.delete_many({"_id": {"$nin": ids}})          # records that left the FDA list
        return len(records)

    async def add_events(self, events):
        if events:
            await self.events.insert_many([to_doc(e) for e in events], ordered=False)
        return len(events)

    async def find_by_ingredient(self, ingredient_rxcui):
        return [self._load(d) async for d in self.col.find({"ingredient_rxcuis": ingredient_rxcui})]

    async def events_for_ingredient(self, ingredient_rxcui, limit=100):
        cursor = self.events.find({"ingredient_rxcuis": ingredient_rxcui}, sort=[("at", -1)], limit=limit)
        return [from_doc(ShortageEvent, d) async for d in cursor]
