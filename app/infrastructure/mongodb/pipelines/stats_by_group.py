"""Pipeline 3: report counts grouped by one attribute (FR-08, ReportRepository.statistics)."""

# group_by -> document path. Missing values are mapped to the model defaults by the repository.
GROUP_FIELDS = {
    "age_group": "$patient.age_group",
    "sex": "$patient.sex",
    "country": "$country",
    "seriousness": "$seriousness.serious",
    "report_type": "$report_type",
    "quarter": "$quarter",
}


def stats_by_group(group_by: str, ingredient_rxcui: str | None, quarter: str | None) -> list[dict]:
    if group_by not in GROUP_FIELDS:
        raise ValueError(f"Unknown group_by {group_by}")
    match: dict = {}
    if quarter:
        match["quarter"] = quarter
    if ingredient_rxcui:
        match["suspect_ingredient_ids"] = ingredient_rxcui
    return [{"$match": match}, {"$group": {"_id": GROUP_FIELDS[group_by], "n": {"$sum": 1}}}]
