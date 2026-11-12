"""explain('executionStats') of the API's main queries, with their index and with a forced collection scan.

    py scripts/benchmark_indexes.py                # needs the dataset in MongoDB (scripts/seed_databases.py)
    py scripts/benchmark_indexes.py --drug 83367   # another ingredient (default: semaglutide)

"Without" uses hint({$natural: 1}), so no index is dropped. The table is the evidence for each index in
app/infrastructure/mongodb/indexes.py: documents examined and time, before and after.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.infrastructure.mongodb.client import create_mongo_client


def _stages(plan: dict) -> list[str]:
    out = [plan.get("stage", "") + (f"({plan['indexName']})" if "indexName" in plan else "")]
    for key in ("inputStage", "queryPlan"):
        if key in plan:
            out += _stages(plan[key])
    for child in plan.get("inputStages", []):
        out += _stages(child)
    return out


async def _explain(cursor) -> tuple[int, int, int, str]:
    e = await cursor.explain()
    stats = e["executionStats"]
    plan = e["queryPlanner"]["winningPlan"]
    return (stats["totalDocsExamined"], stats["totalKeysExamined"], stats["executionTimeMillis"],
            " > ".join(s for s in _stages(plan) if s))


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drug", default="1991302", help="ingredient rxcui (default semaglutide)")
    args = ap.parse_args()
    s = get_settings()
    db = create_mongo_client(s)[s.mongo_db]
    latest = (await db.signals.find_one({}, {"quarter": 1}, sort=[("quarter", -1)]) or {}).get("quarter")
    if latest is None:
        sys.exit("No signals in MongoDB: run scripts/seed_databases.py first.")
    top = await db.signals.find_one({"ingredient_rxcui": args.drug, "is_signal": True}, sort=[("a", -1)])
    reaction = top["reaction_term"] if top else "NAUSEA"
    d = args.drug
    queries = [
        ("signals explorer (quarter, sorted by PRR)", db.signals,
         {"quarter": latest, "a": {"$gte": 20}, "is_signal": True}, [("prr", -1), ("a", -1), ("_id", 1)], 10),
        ("signals of one drug in a quarter", db.signals, {"ingredient_rxcui": d, "quarter": latest},
         [("prr", -1), ("a", -1), ("_id", 1)], 10),
        ("PRR history of one pair (trend)", db.signals, {"ingredient_rxcui": d, "reaction_term": reaction},
         [("quarter", -1)], 6),
        ("reports behind a signal (newest first)", db.reports, {"suspect_ingredient_ids": d, "reaction_pts": reaction},
         [("receive_date", -1), ("_id", -1)], 10),
        ("latest report of a drug (trend window)", db.reports, {"suspect_ingredient_ids": d},
         [("receive_date", -1)], 1),
        ("reports of a quarter (pair counts, stats)", db.reports, {"quarter": latest}, None, 0),
        ("prescription label of a drug", db.labels, {"ingredient_rxcuis": d, "product_type": "RX"}, None, 0),
        ("products of a drug (alternatives)", db.products, {"ingredient_rxcuis": d}, None, 0),
        ("recalls linked to a drug", db.recalls, {"link.ingredient_rxcuis": d, "link.status": "ACCEPTED"}, None, 0),
    ]
    print(f"Drug {d}, reaction {reaction}, quarter {latest}\n")
    print(f"{'query':44s} {'docs examined':>21s} {'keys':>8s} {'ms':>13s}  plan with index")
    print(f"{'':44s} {'no index':>10s} {'index':>10s} {'':>8s} {'no idx':>6s} {'idx':>6s}")
    for name, col, query, sort, limit in queries:
        def cursor(col=col, query=query, sort=sort, limit=limit):
            c = col.find(query)
            if sort:
                c = c.sort(sort)
            return c.limit(limit) if limit else c
        scan = await _explain(cursor().hint([("$natural", 1)]))
        idx = await _explain(cursor())
        print(f"{name:44s} {scan[0]:>10d} {idx[0]:>10d} {idx[1]:>8d} {scan[2]:>6d} {idx[2]:>6d}  {idx[3]}")


if __name__ == "__main__":
    asyncio.run(main())
