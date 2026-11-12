from collections.abc import Iterable
from datetime import datetime

from app.domain.entities.enums import ShortageStatus
from app.domain.entities.shortage import ShortageRecord, ShortageSummary

_SEVERITY = {ShortageStatus.CURRENT: 0, ShortageStatus.TO_BE_DISCONTINUED: 1, ShortageStatus.RESOLVED: 2}


def worst_status(records: Iterable[ShortageRecord]) -> ShortageStatus | None:
    statuses = [r.status for r in records]
    return min(statuses, key=lambda s: _SEVERITY[s]) if statuses else None


def summarize(ingredient_rxcui: str, records: list[ShortageRecord], now: datetime | None = None) -> ShortageSummary:
    return ShortageSummary(
        ingredient_rxcui=ingredient_rxcui,
        worst_status=worst_status(records),
        packages_in_shortage=sum(1 for r in records if r.status is ShortageStatus.CURRENT),
        packages_total=len(records),
        dosage_forms=sorted({r.dosage_form for r in records if r.dosage_form}),
        updated_at=now,
    )
