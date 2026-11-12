import time

from app.application.ports.ingredient_repository import IngredientRepository
from app.domain.entities.drug import Drug
from app.domain.services.name_search import best_matches, normalize_query
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc

_CACHE_SECONDS = 300
_NAMES = {"name": 1, "synonyms": 1, "brand_names": 1}


class MongoIngredientRepository(IngredientRepository):
    """Collection `ingredients`, `_id` = rxcui.

    Typo-tolerant search (FR-01) needs an edit-distance score that MongoDB Community has no index for. The adapter
    reads the names once (about 3k ingredients, ~100 KB, projection on name/synonyms/brand_names), keeps them for
    5 minutes or until a write through this adapter, scores them with the same function as the memory adapter, then
    fetches only the winning documents by _id.
    """

    def __init__(self, db) -> None:
        self.col = db["ingredients"]
        self._names: list[tuple[str, str, list[str]]] | None = None
        self._loaded_at = 0.0

    def _load(self, doc):
        return from_doc(Drug, doc, "rxcui")

    async def get(self, rxcui):
        return self._load(await self.col.find_one({"_id": rxcui}))

    async def get_many(self, rxcuis):
        found = {d["_id"]: d async for d in self.col.find({"_id": {"$in": list(rxcuis)}})}
        return [self._load(found[r]) for r in rxcuis if r in found]

    async def _name_list(self):
        if self._names is None or time.monotonic() - self._loaded_at > _CACHE_SECONDS:
            self._names = [(d["_id"], d["name"], [d["name"], *d.get("synonyms", []), *d.get("brand_names", [])])
                           async for d in self.col.find({}, _NAMES)]
            self._loaded_at = time.monotonic()
        return self._names

    async def search(self, query, limit=10):
        q = normalize_query(query)
        if not q:
            return []
        hits = best_matches(q, await self._name_list(), limit)
        drugs = {d.rxcui: d for d in await self.get_many([rx for rx, _, _ in hits])}
        return [(drugs[rx], text, score) for rx, text, score in hits if rx in drugs]

    async def list_by_class(self, class_id):
        return [self._load(d) async for d in self.col.find({"atc.class_id": class_id})]

    async def upsert_many(self, drugs):
        self._names = None
        return await replace_many(self.col, [to_doc(d, "rxcui") for d in drugs])

    async def count(self):
        return await self.col.count_documents({})
