"""FR-09: the individual reports behind a signal."""
from app.application.dtos.signals import ReportBrief, SignalReports
from app.application.ports.ingredient_repository import IngredientRepository
from app.application.ports.report_repository import ReportRepository
from app.domain.entities.enums import DrugRole
from app.domain.value_objects.reaction_term import normalize_reaction


class SignalReportsUseCase:
    def __init__(self, reports: ReportRepository, ingredients: IngredientRepository) -> None:
        self.reports, self.ingredients = reports, ingredients

    async def execute(self, rxcui: str, reaction: str, skip: int = 0, limit: int = 50) -> SignalReports:
        found, total = await self.reports.list_for_pair(rxcui, normalize_reaction(reaction), skip, limit)
        items = [ReportBrief(
            report_id=r.report_id, receive_date=r.receive_date.isoformat(), serious=r.seriousness.serious,
            age_group=r.patient.age_group.value, sex=r.patient.sex.value, country=r.country,
            reactions=r.reaction_pts,
            suspect_drugs=[d.raw_name or ", ".join(d.active_substances) for d in r.drugs if d.role is DrugRole.SUSPECT and (d.raw_name or d.active_substances)]
        ) for r in found]
        return SignalReports(items=items, total=total)
