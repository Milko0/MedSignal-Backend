"""Pipeline 1: the counts behind every 2x2 table of one quarter (ReportRepository.pair_counts).

Three pipelines instead of one $facet: a $facet result is a single document (16 MB cap) and a quarter has about
100k distinct drug-reaction pairs. Each starts with $match on the {quarter: 1} index. reaction_pts and the id
arrays are de-duplicated per report by the transformer, so $unwind counts each report once. Excluded terms are
removed AFTER $unwind: a report with one excluded term still counts for its other reactions. PRR is computed in
the domain (domain/services/signal_calculator.py) so it stays unit-testable.
"""


def drug_counts(quarter: str, drug_field: str) -> list[dict]:
    return [
        {"$match": {"quarter": quarter}},
        {"$project": {"_id": 0, "d": f"${drug_field}"}},
        {"$unwind": "$d"},
        {"$group": {"_id": "$d", "n": {"$sum": 1}}},
    ]


def reaction_counts(quarter: str, excluded_terms: list[str]) -> list[dict]:
    return [
        {"$match": {"quarter": quarter}},
        {"$project": {"_id": 0, "r": "$reaction_pts"}},
        {"$unwind": "$r"},
        {"$match": {"r": {"$nin": excluded_terms}}},
        {"$group": {"_id": "$r", "n": {"$sum": 1}}},
    ]


def pair_counts(quarter: str, drug_field: str, excluded_terms: list[str]) -> list[dict]:
    return [
        {"$match": {"quarter": quarter, f"{drug_field}.0": {"$exists": True}}},   # reports with a resolved drug
        {"$project": {"_id": 0, "d": f"${drug_field}",
                      "r": {"$setDifference": ["$reaction_pts", excluded_terms]}}},
        {"$unwind": "$d"},
        {"$unwind": "$r"},
        {"$group": {"_id": {"d": "$d", "r": "$r"}, "n": {"$sum": 1}}},
    ]


def top_reactions(ingredient_rxcui: str, drug_field: str, excluded_terms: list[str], limit: int) -> list[dict]:
    return [
        {"$match": {drug_field: ingredient_rxcui}},
        {"$project": {"_id": 0, "r": "$reaction_pts"}},
        {"$unwind": "$r"},
        {"$match": {"r": {"$nin": excluded_terms}}},
        {"$group": {"_id": "$r", "n": {"$sum": 1}}},
        {"$sort": {"n": -1, "_id": 1}},
        {"$limit": limit},
    ]


def monthly_trend(ingredient_rxcui: str, reactions: list[str], first_day: str) -> list[dict]:
    """Suspect reports per (YYYY-MM, reaction) from first_day on (receive_date is an ISO date string)."""
    return [
        {"$match": {"suspect_ingredient_ids": ingredient_rxcui, "receive_date": {"$gte": first_day},
                    "reaction_pts": {"$in": reactions}}},
        {"$project": {"_id": 0, "m": {"$substrBytes": ["$receive_date", 0, 7]}, "r": "$reaction_pts"}},
        {"$unwind": "$r"},
        {"$match": {"r": {"$in": reactions}}},
        {"$group": {"_id": {"m": "$m", "r": "$r"}, "n": {"$sum": 1}}},
    ]
