"""FR-30: build every 2x2 table of a quarter from the pair counts and store the signals.

One pass over the reports (done by the repository), then pure arithmetic here:
  a = reports with drug and reaction      b = reports with the drug, without the reaction
  c = reports with the reaction, other drugs   d = everything else
"""
from collections import defaultdict
from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.excluded_term_repository import ExcludedTermRepository
from app.application.ports.label_repository import LabelRepository
from app.application.ports.report_repository import ReportRepository
from app.application.ports.signal_repository import SignalRepository
from app.domain.entities.enums import LabelMatch, ProductType, RoleFilter
from app.domain.entities.signal import SafetySignal
from app.domain.services.emerging_signal_policy import is_emerging, meets_evans_criteria
from app.domain.services.label_gap_matcher import match_level
from app.domain.services.signal_calculator import compute_signal
from app.domain.value_objects.contingency_table import ContingencyTable


@dataclass
class SignalRunStats:
    quarter: str
    reports: int = 0
    pairs_seen: int = 0
    pairs_stored: int = 0
    signals: int = 0
    emerging: int = 0


class ComputeQuarterSignals:
    def __init__(self, reports: ReportRepository, signals: SignalRepository, labels: LabelRepository,
                 excluded_terms: ExcludedTermRepository, clock: Clock) -> None:
        self.reports, self.signals, self.labels = reports, signals, labels
        self.excluded_terms, self.clock = excluded_terms, clock

    async def _label_texts(self) -> dict[str, str]:
        return {}

    async def execute(self, quarter: str, role_filter: RoleFilter = RoleFilter.SUSPECT, min_a: int = 3) -> SignalRunStats:
        excluded = await self.excluded_terms.as_set()
        pc = await self.reports.pair_counts(quarter, role_filter, excluded)
        stats = SignalRunStats(quarter=quarter, reports=pc.total, pairs_seen=len(pc.per_pair))
        now = self.clock.now()
        label_text: dict[str, str] = {}

        async def text_for(drug: str) -> str:
            if drug not in label_text:
                labels = await self.labels.find_by_ingredient(drug, ProductType.RX)
                label_text[drug] = "\n".join(x.sections.get(k, "") for x in labels
                                             for k in ("adverse_reactions", "warnings", "boxed_warning"))
            return label_text[drug]

        by_drug: dict[str, list[SafetySignal]] = defaultdict(list)
        for (drug, reaction), a in pc.per_pair.items():
            if a < min_a:
                continue
            n_drug, n_reaction = pc.per_drug[drug], pc.per_reaction[reaction]
            table = ContingencyTable(a=a, b=n_drug - a, c=n_reaction - a, d=pc.total - n_drug - n_reaction + a)
            metrics = compute_signal(table)
            if metrics is None:
                continue
            flagged = meets_evans_criteria(metrics, a)
            emerging = False
            level = LabelMatch.NONE
            if flagged:
                previous = await self.signals.previous_prrs(drug, reaction, quarter)
                emerging = is_emerging(metrics.prr, previous)
                level = match_level(reaction, await text_for(drug))
            sig = SafetySignal(
                signal_id=SafetySignal.make_id(quarter, drug, reaction, role_filter.value), quarter=quarter,
                ingredient_rxcui=drug, reaction_term=reaction, a=table.a, b=table.b, c=table.c, d=table.d,
                prr=metrics.prr, ci_lower=metrics.ci_lower, chi_square=metrics.chi_square, is_signal=flagged,
                is_emerging=emerging, label_match=level, role_filter=role_filter, computed_at=now)
            by_drug[drug].append(sig)
            stats.signals += flagged
            stats.emerging += emerging
        batch = [s for sigs in by_drug.values() for s in sigs]
        stats.pairs_stored = len(batch)
        if batch:
            await self.signals.upsert_many(batch)
        return stats
