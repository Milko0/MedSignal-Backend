"""FR-02: the Drug 360 page. Live shortage state comes from the key-value store (cache-aside), the rest from documents."""
from app.application.dtos.drugs import (
    AtcClass,
    Drug360Response,
    LabelSummary,
    ReactionCount,
    RecallsInfo,
    ShortageInfo,
)
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.follow_store import FollowStore
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.domain.entities.enums import (
    ProductType,
    RecallClass,
    RoleFilter,
    ShortageStatus,
)
from app.domain.exceptions import NotFoundError
from app.domain.services.shortage_summary import summarize

CACHE_TTL_SECONDS = 3600


class GetDrug360:
    def __init__(self, ingredients: IngredientRepository, shortages: ShortageRepository,
                 shortage_status: ShortageStatusStore, recalls: RecallRepository, labels: LabelRepository,
                 reports: ReportRepository, follows: FollowStore, excluded_terms: ExcludedTermRepository,
                 clock) -> None:
        self.ingredients, self.shortages, self.shortage_status = ingredients, shortages, shortage_status
        self.recalls, self.labels, self.reports = recalls, labels, reports
        self.follows, self.excluded_terms, self.clock = follows, excluded_terms, clock

    async def _shortage(self, rxcui: str, dosage_form: str | None, route: str | None) -> ShortageInfo:
        all_records = await self.shortages.find_by_ingredient(rxcui)
        forms = sorted({r.dosage_form for r in all_records if r.dosage_form})
        records = all_records
        if dosage_form:
            records = [r for r in records if r.dosage_form == dosage_form.upper()]
        if route:
            records = [r for r in records if route.upper() in r.routes]
        if not dosage_form and not route:
            # cache-aside on the unfiltered summary
            summary = await self.shortage_status.get(rxcui)
            if summary is None:
                summary = summarize(rxcui, records, self.clock.now())
                await self.shortage_status.set(summary, CACHE_TTL_SECONDS)
        else:
            summary = summarize(rxcui, records, self.clock.now())
        current = [r for r in records if r.status is ShortageStatus.CURRENT]
        since = min((r.initial_posting_date for r in current if r.initial_posting_date), default=None)
        reasons = sorted({r.shortage_reason for r in current if r.shortage_reason})
        return ShortageInfo(status=summary.worst_status.value if summary.worst_status else None,
                            packages_in_shortage=summary.packages_in_shortage, packages_total=summary.packages_total,
                            dosage_forms=forms, since=since.isoformat() if since else None, reasons=reasons[:3])

    async def execute(self, rxcui: str, user_id: str | None = None, dosage_form: str | None = None,
                      route: str | None = None) -> Drug360Response:
        drug = await self.ingredients.get(rxcui)
        if drug is None:
            raise NotFoundError(f"Unknown ingredient {rxcui}")

        recalls = await self.recalls.find_by_ingredient(rxcui, accepted_only=True)
        counts = {c: sum(1 for r in recalls if r.classification is c) for c in RecallClass}
        recalls_info = RecallsInfo(
            class_i=counts[RecallClass.CLASS_I], class_ii=counts[RecallClass.CLASS_II],
            class_iii=counts[RecallClass.CLASS_III], not_classified=counts[RecallClass.NOT_CLASSIFIED],
            total=len(recalls), linked_share=round(await self.recalls.linked_share(), 3))

        labels = await self.labels.find_by_ingredient(rxcui)
        rx = sorted((x for x in labels if x.product_type is ProductType.RX), key=lambda x: x.effective_date or __import__("datetime").date.min, reverse=True)
        chosen = (rx or labels or [None])[0]
        label = LabelSummary(available=bool(labels), product_types=sorted({x.product_type.value for x in labels}))
        if chosen:
            text = chosen.sections.get("indications_and_usage", "")
            label = label.model_copy(update={
                "effective_date": chosen.effective_date.isoformat() if chosen.effective_date else None,
                "has_boxed_warning": any(x.has_boxed_warning for x in labels),
                "description": (text[:400] + "...") if len(text) > 400 else (text or None)})

        excluded = await self.excluded_terms.as_set()
        top = await self.reports.top_reactions(rxcui, 10, RoleFilter.SUSPECT, excluded)
        followed = bool(user_id) and await self.follows.is_following(user_id, rxcui)
        return Drug360Response(
            rxcui=drug.rxcui, name=drug.name, brand_names=drug.brand_names[:10],
            atc_classes=[AtcClass(class_id=c.class_id, name=c.name) for c in drug.atc],
            selected_dosage_form=dosage_form.upper() if dosage_form else None,
            selected_route=route.upper() if route else None,
            shortage=await self._shortage(rxcui, dosage_form, route), recalls=recalls_info, label=label,
            top_reactions=[ReactionCount(reaction=r, reports=n) for r, n in top], is_followed=followed,
            match_coverage=round(await self.reports.match_coverage(None), 3))
