"""FR-07: frequently reported reactions the label does not fully mention."""
from app.application.dtos.drugs import LabelGapRow, LabelGapsData
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.report_repository import ReportRepository
from app.domain.entities.enums import ProductType, RoleFilter
from app.domain.services.label_gap_matcher import find_label_gaps

_COMPARED = ("adverse_reactions", "warnings", "boxed_warning")


class GetLabelGaps:
    def __init__(self, reports: ReportRepository, labels: LabelRepository,
                 excluded_terms: ExcludedTermRepository) -> None:
        self.reports, self.labels, self.excluded_terms = reports, labels, excluded_terms

    async def execute(self, rxcui: str, min_reports: int = 20) -> LabelGapsData:
        labels = await self.labels.find_by_ingredient(rxcui)
        if not labels:
            return LabelGapsData(label_available=False, comparable=False, note="No label found for this ingredient.")
        rx = [x for x in labels if x.product_type is ProductType.RX]
        if not rx:
            # OTC labels have no adverse reaction section: a comparison would flag everything
            return LabelGapsData(label_available=True, comparable=False,
                                 note="Only OTC labels exist for this ingredient; they have no adverse reaction section.")
        warnings_text = "\n".join(x.sections.get(k, "") for x in rx for k in _COMPARED)
        indications = "\n".join(x.sections.get("indications_and_usage", "") for x in rx)
        excluded = await self.excluded_terms.as_set()
        reported = await self.reports.top_reactions(rxcui, 100, RoleFilter.SUSPECT, excluded)
        gaps = find_label_gaps(reported, warnings_text, indications, excluded, min_reports)
        return LabelGapsData(label_available=True, comparable=True, gaps=[
            LabelGapRow(reaction=g.reaction_term, reports=g.report_count, match_level=g.match_level.value,
                        in_indications=g.in_indications) for g in gaps])
