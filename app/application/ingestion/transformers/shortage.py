"""openFDA shortage record -> ShortageRecord."""
from collections.abc import Mapping
from datetime import UTC, datetime

from app.application.ingestion.transformers.common import (
    blank_to_none,
    str_list,
    unique,
)
from app.domain.entities.enums import Availability, ShortageStatus
from app.domain.entities.shortage import ShortageRecord
from app.domain.exceptions import TransformError
from app.domain.services.date_parser import parse_day
from app.domain.value_objects.ndc import Ndc

_STATUS = {
    "CURRENT": ShortageStatus.CURRENT,
    "TO BE DISCONTINUED": ShortageStatus.TO_BE_DISCONTINUED,
    "RESOLVED": ShortageStatus.RESOLVED,
}


def normalize_availability(raw) -> Availability:
    """Keeps working with the typos seen in the data (Unvailable, Limited Availalbility)."""
    text = (blank_to_none(raw) or "").lower()
    if not text:
        return Availability.UNKNOWN
    if text.startswith(("unav", "unva")) or "not available" in text:
        return Availability.UNAVAILABLE
    if "limit" in text:
        return Availability.LIMITED
    if text.startswith("avail"):
        return Availability.AVAILABLE
    return Availability.UNKNOWN


def transform_shortage(
    raw: dict,
    product_ingredients: Mapping[str, list[str]] | None = None,
    rx_to_ingredients: Mapping[str, list[str]] | None = None,
    now: datetime | None = None,
) -> ShortageRecord:
    """product_ingredients: product NDC -> ingredient rxcuis (from the NDC directory).
    rx_to_ingredients: product rxcui -> ingredient rxcuis (from RxNav, cached)."""
    now = now or datetime.now(UTC)
    package = blank_to_none(raw.get("package_ndc"))
    if package is None:
        raise TransformError("shortage record without package_ndc")
    try:
        ndc = Ndc.parse(package)
    except ValueError as exc:
        raise TransformError(str(exc)) from exc

    status = _STATUS.get(str(raw.get("status") or "").strip().upper())
    if status is None:
        raise TransformError(f"unknown shortage status: {raw.get('status')!r}")

    openfda = raw.get("openfda") or {}
    ingredients: list[str] = []
    for rx in str_list(openfda.get("rxcui")):
        ingredients += (rx_to_ingredients or {}).get(rx, [])
    if not ingredients:
        ingredients = list((product_ingredients or {}).get(ndc.product_ndc, []))

    availability_raw = blank_to_none(raw.get("availability"))
    form = blank_to_none(raw.get("dosage_form"))
    return ShortageRecord(
        package_ndc=ndc.package_ndc,
        ndc11=ndc.to_ndc11(),
        product_ndc=ndc.product_ndc,
        ingredient_rxcuis=unique(ingredients),
        generic_name=blank_to_none(raw.get("generic_name")),
        dosage_form=form.upper() if form else None,
        routes=[r.upper() for r in str_list(openfda.get("route"))],
        status=status,
        availability=normalize_availability(availability_raw),
        availability_raw=availability_raw,
        shortage_reason=blank_to_none(raw.get("shortage_reason")),
        company=blank_to_none(raw.get("company_name")),
        therapeutic_categories=str_list(raw.get("therapeutic_category")),
        presentation=blank_to_none(raw.get("presentation")),
        initial_posting_date=parse_day(raw.get("initial_posting_date")),
        update_date=parse_day(raw.get("update_date")),
        discontinued_date=parse_day(raw.get("discontinued_date")),
        first_seen=now,
        last_seen=now,
    )
