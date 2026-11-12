"""Event sync: apply one document change to the key-value layer, idempotently.

Called by the MongoDB change-stream projector (infrastructure/sync) for every insert / update / replace:
- a signal: overwrite the live counter count:{ingredient}:{reaction}:{quarter} with its report count `a`
  (SET, never INCR, so a replay changes nothing) and, when it meets the Evans criteria, alert the drug's followers
  (deterministic alert id, so a replay creates nothing new);
- a shortage record: recompute the ingredient's ShortageSummary from the documents and overwrite it.
Shortage, label and recall ALERTS are already sent by the ingestion use cases; this only adds signal alerts.
"""
from app.application.ports.counter_store import CounterStore
from app.application.ports.shortage_repository import ShortageRepository
from app.application.ports.shortage_status_store import ShortageStatusStore
from app.application.services.alert_dispatcher import AlertDispatcher
from app.domain.entities.enums import AlertType, RoleFilter
from app.domain.entities.signal import SafetySignal
from app.domain.services.shortage_summary import summarize

SUMMARY_TTL_SECONDS = 3600


class ProjectChangeEvent:
    def __init__(self, shortages: ShortageRepository, shortage_status: ShortageStatusStore, counters: CounterStore,
                 dispatcher: AlertDispatcher, clock) -> None:
        self.shortages, self.shortage_status, self.counters = shortages, shortage_status, counters
        self.dispatcher, self.clock = dispatcher, clock

    async def signal_changed(self, signal: SafetySignal) -> int:
        """Returns the number of new alerts."""
        if signal.role_filter is not RoleFilter.SUSPECT:
            return 0
        await self.counters.set_count(signal.ingredient_rxcui, signal.reaction_term, signal.quarter, signal.a)
        if not signal.is_signal:
            return 0
        kind = "Emerging signal" if signal.is_emerging else "New signal"
        message = (f"{kind}: {signal.reaction_term.lower()} ({signal.a} reports, PRR {signal.prr:.1f}, "
                   f"{signal.quarter})")
        return await self.dispatcher.dispatch(AlertType.SIGNAL, signal.ingredient_rxcui, signal.signal_id, message,
                                              ref_type="signal", reports=signal.a)

    async def shortage_changed(self, ingredient_rxcuis: list[str]) -> None:
        for rxcui in ingredient_rxcuis:
            records = await self.shortages.find_by_ingredient(rxcui)
            if records:
                await self.shortage_status.set(summarize(rxcui, records, self.clock.now()), SUMMARY_TTL_SECONDS)
            else:
                await self.shortage_status.delete(rxcui)
