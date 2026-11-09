"""Pipeline 1 (part 1): drug-reaction pair counts for one quarter.

Marginals (N, nDrug, nReact) are computed separately and joined; PRR itself is computed in the domain
(domain/services/signal_calculator.py) so it stays unit-testable.
"""


def pair_counts_pipeline(quarter: str, excluded_terms: list[str]) -> list[dict]:
    return [
        {"$match": {"quarter": quarter}},
        {"$project": {
            "drugs": {"$setUnion": ["$drugs.rxcui", []]},  # distinct drugs per report
            "reactions": {"$setDifference": [{"$setUnion": ["$reactions", []]}, excluded_terms]},
        }},
        {"$unwind": "$drugs"},
        {"$unwind": "$reactions"},
        {"$group": {"_id": {"d": "$drugs", "r": "$reactions"}, "a": {"$sum": 1}}},
        {"$match": {"a": {"$gte": 3}}},
    ]
