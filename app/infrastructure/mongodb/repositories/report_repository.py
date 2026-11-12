from datetime import date

from app.application.ports.report_repository import ReportRepository
from app.domain.entities.enums import AgeGroup, ReportType, RoleFilter, Sex
from app.domain.entities.report import AdverseReport
from app.domain.value_objects.pair_counts import PairCounts
from app.infrastructure.mongodb.documents import from_doc, replace_many, to_doc
from app.infrastructure.mongodb.pipelines import signal_counts as p
from app.infrastructure.mongodb.pipelines.stats_by_group import stats_by_group

_AGE_ORDER = [g.value for g in AgeGroup]
_DEFAULTS = {"age_group": AgeGroup.UNKNOWN.value, "sex": Sex.UNKNOWN.value, "country": "UNKNOWN",
             "report_type": ReportType.OTHER.value}
_SERIOUS = {True: "SERIOUS", False: "NON_SERIOUS", None: "UNKNOWN"}


def _drug_field(role_filter: RoleFilter) -> str:
    return "suspect_ingredient_ids" if role_filter is RoleFilter.SUSPECT else "all_ingredient_ids"


class MongoReportRepository(ReportRepository):
    """Collection `reports`, `_id` = report_id. See mongodb/indexes.py for the indexes each query uses."""

    def __init__(self, db) -> None:
        self.col = db["reports"]

    async def upsert_many(self, reports):
        # The filter only matches an older or equal version. A newer stored version makes the upsert try an insert
        # with the same _id, which fails with a duplicate key: that is the "keep the highest version" rule.
        docs = [to_doc(r, "report_id") for r in reports]
        filters = [{"_id": d["_id"], "version": {"$lte": d["version"]}} for d in docs]
        return await replace_many(self.col, docs, filters, ignore_duplicates=True)

    async def get(self, report_id):
        return from_doc(AdverseReport, await self.col.find_one({"_id": report_id}), "report_id")

    async def delete(self, report_id):
        return (await self.col.delete_one({"_id": report_id})).deleted_count == 1

    async def delete_quarter(self, quarter):
        return (await self.col.delete_many({"quarter": quarter})).deleted_count

    async def count(self):
        return await self.col.count_documents({})

    async def quarters(self):
        return sorted(await self.col.distinct("quarter"))

    async def _rows(self, pipeline):
        return [row async for row in await self.col.aggregate(pipeline, allowDiskUse=True)]

    async def pair_counts(self, quarter, role_filter, excluded_terms):
        field, excluded = _drug_field(role_filter), sorted(excluded_terms)
        pc = PairCounts(total=await self.col.count_documents({"quarter": quarter}))
        pc.per_drug = {r["_id"]: r["n"] for r in await self._rows(p.drug_counts(quarter, field))}
        pc.per_reaction = {r["_id"]: r["n"] for r in await self._rows(p.reaction_counts(quarter, excluded))}
        pc.per_pair = {(r["_id"]["d"], r["_id"]["r"]): r["n"]
                       for r in await self._rows(p.pair_counts(quarter, field, excluded))}
        return pc

    async def top_reactions(self, ingredient_rxcui, limit, role_filter, excluded_terms):
        rows = await self._rows(p.top_reactions(ingredient_rxcui, _drug_field(role_filter), sorted(excluded_terms),
                                                limit))
        return [(r["_id"], r["n"]) for r in rows]

    async def monthly_trend(self, ingredient_rxcui, reactions, months):
        if not reactions:
            return []
        latest = await self.col.find_one({"suspect_ingredient_ids": ingredient_rxcui},
                                         {"receive_date": 1}, sort=[("receive_date", -1)])
        if latest is None:
            return []
        last = date.fromisoformat(latest["receive_date"])
        window = []
        y, m = last.year, last.month
        for _ in range(months):
            window.append(f"{y:04d}-{m:02d}")
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        window.reverse()
        rows = await self._rows(p.monthly_trend(ingredient_rxcui, reactions, f"{window[0]}-01"))
        counts = {(r["_id"]["m"], r["_id"]["r"]): r["n"] for r in rows}
        return [(mo, t, counts.get((mo, t), 0)) for mo in window for t in reactions]

    async def list_for_pair(self, ingredient_rxcui, reaction, skip, limit):
        query = {"suspect_ingredient_ids": ingredient_rxcui, "reaction_pts": reaction}
        cursor = self.col.find(query, sort=[("receive_date", -1), ("_id", -1)], skip=skip, limit=limit)
        items = [from_doc(AdverseReport, d, "report_id") async for d in cursor]
        return items, await self.col.count_documents(query)

    async def statistics(self, group_by, ingredient_rxcui, quarter):
        counts: dict[str, int] = {}
        for row in await self._rows(stats_by_group(group_by, ingredient_rxcui, quarter)):
            key = row["_id"]
            if group_by == "seriousness":
                key = _SERIOUS.get(key, "UNKNOWN")
            elif not key:
                key = _DEFAULTS.get(group_by, "UNKNOWN")
            counts[key] = counts.get(key, 0) + row["n"]
        if group_by == "age_group":
            return [(k, counts[k]) for k in _AGE_ORDER if k in counts]
        if group_by == "quarter":
            return sorted(counts.items())
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    async def match_coverage(self, quarter=None):
        base = {"quarter": quarter} if quarter else {}
        total = await self.col.count_documents(base)
        if not total:
            return 0.0
        return await self.col.count_documents({**base, "all_ingredient_ids.0": {"$exists": True}}) / total
