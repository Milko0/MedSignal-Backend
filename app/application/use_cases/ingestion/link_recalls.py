"""Propose drug candidates for recalls that have no openFDA ids. Candidates are never accepted automatically."""
import re
from dataclasses import dataclass

from app.application.ports.clock import Clock
from app.application.ports.drug_normalizer import DrugNormalizer
from app.application.ports.recall_repository import RecallRepository
from app.domain.entities.enums import LinkMethod, LinkStatus
from app.domain.entities.recall import LinkCandidate, Recall


def description_key(text: str | None) -> str:
    """The product description starts with the drug name: 'Semaglutide Injection, 2.5 mg/mL...' -> 'Semaglutide Injection'."""
    return re.split(r"[,;(\d]", text or "")[0].strip()[:60]


@dataclass
class LinkStats:
    examined: int = 0
    proposed: int = 0
    no_candidate: int = 0


class LinkRecalls:
    def __init__(self, recalls: RecallRepository, normalizer: DrugNormalizer, clock: Clock) -> None:
        self.recalls, self.normalizer, self.clock = recalls, normalizer, clock

    async def execute(self, min_score: float = 10.0, max_recalls: int | None = None) -> LinkStats:
        stats = LinkStats()
        updated: list[Recall] = []
        for recall in await self.recalls.all():
            if recall.link.status is not LinkStatus.UNREVIEWED or recall.link.candidates:
                continue
            if max_recalls is not None and stats.examined >= max_recalls:
                break
            stats.examined += 1
            key = description_key(recall.product_description)
            candidates = await self.normalizer.approximate(key) if key else []
            good = [LinkCandidate(rxcui=c.rxcui, name=c.name or "", score=c.score) for c in candidates
                    if (c.score or 0) >= min_score]
            if not good:
                stats.no_candidate += 1
                continue
            stats.proposed += 1
            link = recall.link.model_copy(update={"status": LinkStatus.CANDIDATE, "method": LinkMethod.TEXT,
                                                  "candidates": good})
            updated.append(recall.model_copy(update={"link": link}))
        if updated:
            await self.recalls.upsert_many(updated)
        return stats
