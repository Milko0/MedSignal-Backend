from app.application.ports.recall_repository import RecallRepository
from app.domain.entities.enums import LinkStatus
from app.domain.entities.recall import Recall
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc

_ACCEPTED = LinkStatus.ACCEPTED.value


class MongoRecallRepository(RecallRepository):
    """`recalls`, `_id` = recall_number. The link to ingredients is explicit and auditable (`link.status`)."""

    def __init__(self, db) -> None:
        self.col = db["recalls"]

    def _load(self, doc):
        return from_doc(Recall, doc, "recall_number")

    async def upsert_many(self, recalls):
        return await replace_many(self.col, [to_doc(r, "recall_number") for r in recalls])

    async def all(self):
        return [self._load(d) async for d in self.col.find({})]

    async def find_by_ingredient(self, ingredient_rxcui, accepted_only=True):
        query: dict = {"link.status": _ACCEPTED, "link.ingredient_rxcuis": ingredient_rxcui}
        if not accepted_only:
            query = {"$or": [query, {"link.candidates.rxcui": ingredient_rxcui}]}
        return [self._load(d) async for d in self.col.find(query)]

    async def linked_share(self):
        total = await self.col.count_documents({})
        return await self.col.count_documents({"link.status": _ACCEPTED}) / total if total else 0.0
