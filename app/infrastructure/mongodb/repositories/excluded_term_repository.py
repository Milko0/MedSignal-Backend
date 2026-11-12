from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.domain.entities.excluded_term import ExcludedTerm
from app.infrastructure.mongodb.documents import from_doc, to_doc


class MongoExcludedTermRepository(ExcludedTermRepository):
    """`excluded_terms`, `_id` = term (upper case)."""

    def __init__(self, db) -> None:
        self.col = db["excluded_terms"]

    async def list(self):
        return [from_doc(ExcludedTerm, d, "term") async for d in self.col.find({}, sort=[("_id", 1)])]

    async def add(self, term):
        doc = to_doc(term, "term")
        await self.col.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def remove(self, term):
        return (await self.col.delete_one({"_id": term})).deleted_count == 1
