from app.application.ports.signal_repository import SignalRepository
from app.domain.entities.signal import SafetySignal
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc


class MongoSignalRepository(SignalRepository):
    """Collection `signals`, `_id` = signal_id (quarter|ingredient|reaction|role_filter)."""

    def __init__(self, db) -> None:
        self.col = db["signals"]

    def _load(self, doc):
        return from_doc(SafetySignal, doc, "signal_id")

    async def upsert_many(self, signals):
        return await replace_many(self.col, [to_doc(s, "signal_id") for s in signals])

    async def search(self, quarter, ingredient_rxcui, reaction, min_reports, only_signals, only_emerging, skip, limit):
        query: dict = {"quarter": quarter, "a": {"$gte": min_reports}}
        if ingredient_rxcui is not None:
            query["ingredient_rxcui"] = ingredient_rxcui
        if reaction is not None:
            query["reaction_term"] = reaction
        if only_signals:
            query["is_signal"] = True
        if only_emerging:
            query["is_emerging"] = True
        cursor = self.col.find(query, sort=[("prr", -1), ("a", -1), ("_id", 1)], skip=skip, limit=limit)
        return [self._load(d) async for d in cursor], await self.col.count_documents(query)

    async def _prrs(self, query, n):
        cursor = self.col.find(query, {"prr": 1, "quarter": 1}, sort=[("quarter", -1)], limit=n)
        return [d["prr"] async for d in cursor][::-1]          # newest n, returned oldest first

    async def previous_prrs(self, ingredient_rxcui, reaction, quarter, n=4):
        return await self._prrs({"ingredient_rxcui": ingredient_rxcui, "reaction_term": reaction,
                                 "quarter": {"$lt": quarter}}, n)

    async def trend(self, ingredient_rxcui, reaction, n=6):
        return await self._prrs({"ingredient_rxcui": ingredient_rxcui, "reaction_term": reaction}, n)

    async def signal_count(self, ingredient_rxcui, quarter):
        return await self.col.count_documents({"ingredient_rxcui": ingredient_rxcui, "quarter": quarter,
                                               "is_signal": True})

    async def latest_quarter(self):
        doc = await self.col.find_one({}, {"quarter": 1}, sort=[("quarter", -1)])
        return doc["quarter"] if doc else None

    async def delete_quarter(self, quarter):
        return (await self.col.delete_many({"quarter": quarter})).deleted_count
