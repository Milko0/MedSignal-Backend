"""Model <-> document mapping shared by the repositories.

The natural id of each model becomes `_id` (docs/PORT_CONTRACT.md) and is not stored twice. None values are left
out; defaults are kept so queries and aggregations can rely on every field being present.
"""
from pymongo import ReplaceOne
from pymongo.errors import BulkWriteError

DUPLICATE_KEY = 11000


def to_doc(model, id_field: str | None = None, **extra) -> dict:
    doc = model.model_dump(mode="json", exclude_none=True)
    if id_field:
        doc["_id"] = doc.pop(id_field)
    doc.update(extra)
    return doc


def from_doc(model_cls, doc: dict | None, id_field: str | None = None):
    if doc is None:
        return None
    if id_field:
        doc[id_field] = doc.pop("_id")
    return model_cls.model_validate(doc)   # unknown helper fields (search_terms, ...) are ignored


async def replace_many(collection, docs: list[dict], filters: list[dict] | None = None,
                       ignore_duplicates: bool = False) -> int:
    """Upsert every document by `_id` (or by the given filters) in one unordered bulk write."""
    if not docs:
        return 0
    filters = filters or [{"_id": d["_id"]} for d in docs]
    ops = [ReplaceOne(f, d, upsert=True) for f, d in zip(filters, docs, strict=True)]
    try:
        await collection.bulk_write(ops, ordered=False)
    except BulkWriteError as exc:
        errors = exc.details.get("writeErrors", [])
        if not ignore_duplicates or any(e.get("code") != DUPLICATE_KEY for e in errors):
            raise
    return len(docs)
