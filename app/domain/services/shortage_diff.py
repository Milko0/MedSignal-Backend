"""Compares two daily snapshots of the shortage list and returns what changed (our own history, FR-28)."""
from collections.abc import Iterable, Mapping
from datetime import datetime

from app.domain.entities.enums import EventKind
from app.domain.entities.shortage import ShortageEvent, ShortageRecord


def diff_shortages(
    previous: Mapping[str, ShortageRecord],
    current: Iterable[ShortageRecord],
    now: datetime,
    initial: bool = False,
) -> tuple[list[ShortageRecord], list[ShortageEvent]]:
    """Returns (new current records, events).

    initial=True is the first snapshot: records are stored but no APPEARED events are emitted (it would be noise).
    A record that disappears from the list produces a DISAPPEARED event and is not part of the new current set.
    """
    records: list[ShortageRecord] = []
    events: list[ShortageEvent] = []
    seen: set[str] = set()
    for rec in current:
        seen.add(rec.package_ndc)
        old = previous.get(rec.package_ndc)
        if old is None:
            records.append(rec.model_copy(update={"first_seen": now, "last_seen": now}))
            if not initial:
                events.append(ShortageEvent(package_ndc=rec.package_ndc, at=now, kind=EventKind.APPEARED,
                                            to_status=rec.status, ingredient_rxcuis=rec.ingredient_rxcuis))
            continue
        records.append(rec.model_copy(update={"first_seen": old.first_seen or now, "last_seen": now}))
        if old.status != rec.status:
            events.append(ShortageEvent(package_ndc=rec.package_ndc, at=now, kind=EventKind.STATUS_CHANGE,
                                        from_status=old.status, to_status=rec.status,
                                        ingredient_rxcuis=rec.ingredient_rxcuis))
    for package, old in previous.items():
        if package not in seen:
            events.append(ShortageEvent(package_ndc=package, at=now, kind=EventKind.DISAPPEARED,
                                        from_status=old.status, ingredient_rxcuis=old.ingredient_rxcuis))
    return records, events
