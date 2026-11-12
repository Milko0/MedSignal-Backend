"""All MongoDB indexes in one place. Each line says which port query it serves; validate with explain()
(scripts/benchmark_indexes.py). `_id` is always the natural id (docs/PORT_CONTRACT.md), so lookups by id need none.

A compound index may contain at most ONE array field (MongoDB rejects "parallel arrays"): that is why
suspect_ingredient_ids is paired with receive_date and not with reaction_pts.
"""
from pymongo import ASCENDING as ASC
from pymongo import DESCENDING as DESC
from pymongo import IndexModel

INDEXES: dict[str, list[IndexModel]] = {
    "reports": [
        IndexModel([("quarter", ASC)], name="quarter"),          # pair_counts, statistics, delete_quarter, distinct
        # monthly_trend (latest report + window), list_for_pair (sorted newest first), top_reactions, Drug 360 stats
        IndexModel([("suspect_ingredient_ids", ASC), ("receive_date", DESC), ("_id", DESC)], name="suspect_date"),
    ],
    "signals": [
        # explorer: equality on quarter + is_signal, then the sort order itself, so no in-memory sort and LIMIT stops early
        IndexModel([("quarter", ASC), ("is_signal", ASC), ("prr", DESC), ("a", DESC), ("_id", ASC)], name="explorer"),
        IndexModel([("ingredient_rxcui", ASC), ("quarter", ASC), ("prr", DESC)], name="drug_quarter"),  # drug page
        IndexModel([("ingredient_rxcui", ASC), ("reaction_term", ASC), ("quarter", DESC)], name="history"),  # trend
    ],
    "ingredients": [IndexModel([("atc.class_id", ASC)], name="atc_class")],               # same-class alternatives
    "products": [IndexModel([("ingredient_rxcuis", ASC), ("dosage_form", ASC)], name="ingredient_form")],
    "labels": [IndexModel([("ingredient_rxcuis", ASC), ("product_type", ASC)], name="ingredient_type")],
    "shortages": [IndexModel([("ingredient_rxcuis", ASC)], name="ingredient")],
    "shortage_events": [IndexModel([("ingredient_rxcuis", ASC), ("at", DESC)], name="ingredient_at")],
    "recalls": [
        IndexModel([("link.ingredient_rxcuis", ASC), ("link.status", ASC)], name="linked"),
        IndexModel([("link.candidates.rxcui", ASC)], name="candidates"),
    ],
    "name_map": [IndexModel([("status", ASC)], name="status")],                             # review queue
    "users": [
        IndexModel([("username_lower", ASC)], unique=True, name="username"),
        IndexModel([("email_lower", ASC)], unique=True, name="email"),
    ],
    "ingestion_runs": [IndexModel([("started_at", DESC)], name="started_at")],
}


async def ensure_indexes(db) -> None:
    """Creates the declared indexes and drops the ones no longer declared, so every database matches this file."""
    for name, models in INDEXES.items():
        wanted = {m.document["name"] for m in models}
        async for index in await db[name].list_indexes():
            if index["name"] != "_id_" and index["name"] not in wanted:
                await db[name].drop_index(index["name"])
        await db[name].create_indexes(models)
