"""Drug 360 card (FR-02): cache-aside for shortage status, Mongo for the heavy data."""
from app.application.ports.drug_repository import DrugRepository
from app.application.ports.follow_store import FollowStore
from app.application.ports.label_repository import LabelRepository
from app.application.ports.recall_repository import RecallRepository
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.application.ports.signal_repository import SignalRepository
from app.core.constants import SHORTAGE_CACHE_TTL_SECONDS
from app.domain.exceptions import NotFoundError


class GetDrug360:
    def __init__(self, drugs: DrugRepository, status_store: ShortageStatusStore, shortages: ShortageRepository,
                 signals: SignalRepository, labels: LabelRepository, recalls: RecallRepository, follows: FollowStore):
        self._drugs, self._status_store, self._shortages = drugs, status_store, shortages
        self._signals, self._labels, self._recalls, self._follows = signals, labels, recalls, follows

    async def execute(self, rxcui: str, user_id: str | None = None) -> dict:
        drug = await self._drugs.get(rxcui)
        if drug is None:
            raise NotFoundError(f"Drug {rxcui} not found")
        # cache-aside: Redis first, Mongo on miss, then refill with TTL
        status = await self._status_store.get(rxcui)
        if status is None:
            status = await self._shortages.latest_status(rxcui)
            if status is not None:
                await self._status_store.set(rxcui, status, ttl_seconds=SHORTAGE_CACHE_TTL_SECONDS)
        followed = await self._follows.is_following(user_id, rxcui) if user_id else False
        return {
            "drug": drug,
            "shortage": status,
            "recalls": await self._recalls.counts_by_class(rxcui),
            "label": await self._labels.summary_for_drug(rxcui),
            "top_signals": await self._signals.top_for_drug(rxcui, limit=5),
            "is_followed": followed,
        }
