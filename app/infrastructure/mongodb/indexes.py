"""All MongoDB indexes in one place (justify and validate each with explain() before/after)."""
from pymongo import ASCENDING, DESCENDING, IndexModel

INDEXES: dict[str, list[IndexModel]] = {
    "reports": [
        IndexModel([("safety_report_id", ASCENDING)], unique=True),
        IndexModel([("drugs.rxcui", ASCENDING), ("reactions", ASCENDING), ("quarter", ASCENDING)]),
        IndexModel([("receive_date", DESCENDING)]),
    ],
    "labels": [
        IndexModel([("set_id", ASCENDING)], unique=True),
        IndexModel([("rxcui", ASCENDING), ("product_type", ASCENDING)]),
    ],
    "signals": [
        IndexModel([("quarter", ASCENDING), ("rxcui", ASCENDING), ("reaction", ASCENDING)], unique=True),
        IndexModel([("quarter", ASCENDING), ("prr", DESCENDING)]),
    ],
    "shortages": [IndexModel([("rxcui", ASCENDING), ("status_date", DESCENDING)])],
    "recalls": [IndexModel([("rxcui", ASCENDING), ("classification", ASCENDING)])],
    "drugs": [IndexModel([("rxcui", ASCENDING)], unique=True), IndexModel([("names_lower", ASCENDING)])],
    "users": [IndexModel([("email", ASCENDING)], unique=True), IndexModel([("username", ASCENDING)], unique=True)],
    "excluded_terms": [IndexModel([("term", ASCENDING)], unique=True)],
    "ingestion_runs": [IndexModel([("started_at", DESCENDING)])],
}


async def ensure_indexes(db) -> None:
    for name, models in INDEXES.items():
        await db[name].create_indexes(models)
