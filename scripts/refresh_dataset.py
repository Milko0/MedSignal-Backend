"""Improves an existing data/clean WITHOUT the full build (no FAERS re-read, almost no RxNav calls).

    python -m scripts.refresh_dataset                       # brands + targeted labels + signals, then export
    python -m scripts.refresh_dataset --skip-labels         # only brands and signals (offline)

Steps:
  1. brand names of every ingredient from the NDC products (search finds "Ozempic", "Lipitor")
  2. labels for the drugs that HAVE signals but no prescription label yet (openFDA /drug/label by ingredient name),
     newest first; the raw pages are appended to data/raw/labels.jsonl so the next full build has them too
  3. signals recomputed for every quarter (oldest first): label_match and label gaps use the new labels
  4. export back to data/clean (same files, same format)
"""
import argparse
import asyncio
import json
import logging
import time
from collections import Counter
from pathlib import Path

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver, run_bounded
from app.application.use_cases.ingestion.attach_brand_names import AttachBrandNames
from app.application.use_cases.ingestion.compute_quarter_signals import ComputeQuarterSignals
from app.application.use_cases.ingestion.update_labels_recalls import UpdateLabelsAndRecalls
from app.core.config import get_settings
from app.domain.entities.enums import ProductType, RoleFilter
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer
from app.infrastructure.memory.dataset import export_dataset
from app.infrastructure.memory.factory import build_loaded_container

log = logging.getLogger("medsignal.refresh")


class ListFeeds:
    """Label feed over the pages we just fetched; no recalls (they are already in the dataset)."""

    def __init__(self, labels: list[dict]) -> None:
        self.labels = labels

    async def fetch_labels(self, limit=None):
        for r in self.labels[:limit]:
            yield r

    async def fetch_recalls(self, limit=None):
        return
        yield  # an empty async generator


async def label_coverage(c, ingredient_ids) -> int:
    return sum([1 for i in ingredient_ids if await c.labels.find_by_ingredient(i, ProductType.RX)])


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=None, help="clean dataset folder (default DATA_DIR)")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--skip-labels", action="store_true")
    ap.add_argument("--min-reports", type=int, default=10, help="target drugs with at least this many signal reports")
    ap.add_argument("--max-drugs", type=int, default=600, help="at most this many drugs get new labels")
    ap.add_argument("--labels-per-drug", type=int, default=2)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    started = time.monotonic()
    s = get_settings()
    data_dir = a.data or s.data_dir

    log.info("loading %s", data_dir)
    c = await build_loaded_container(data_dir)

    log.info("1/4 brand names")
    log.info("    %d ingredients got brand names", await AttachBrandNames(c.ingredients).execute(c.products.all_items()))

    signal_reports: Counter = Counter()
    for sig in c.signals.all_items():
        if sig.is_signal:
            signal_reports[sig.ingredient_rxcui] += sig.a
    targets = [i for i, n in signal_reports.most_common() if n >= a.min_reports]
    before = await label_coverage(c, targets)

    if not a.skip_labels:
        missing = [i for i in targets if not await c.labels.find_by_ingredient(i, ProductType.RX)][:a.max_drugs]
        log.info("2/4 labels: %d drugs with signals, %d have an Rx label, fetching for %d", len(targets), before,
                 len(missing))
        drugs = {d.rxcui: d for d in await c.ingredients.get_many(missing)}
        fda = HttpFetcher(s.openfda_requests_per_second, s.http_max_retries, s.http_timeout_seconds)
        feeds = OpenFdaFeeds(s, fda)
        pages = await run_bounded([drugs[i].name for i in missing if i in drugs],
                                  lambda n: feeds.labels_for_ingredient(n, a.labels_per_drug), 4, "label searches")
        raw = list({r["set_id"]: r for page in pages for r in page if r.get("set_id")}.values())
        await fda.aclose()
        raw_file = Path(a.raw_dir) / "labels.jsonl"
        if raw_file.parent.exists():
            known = set()
            if raw_file.exists():
                with open(raw_file, encoding="utf-8") as f:
                    known = {json.loads(line).get("set_id") for line in f if line.strip()}
            with open(raw_file, "a", encoding="utf-8") as f:
                f.writelines(json.dumps(r) + "\n" for r in raw if r["set_id"] not in known)
        rx = HttpFetcher(s.rxnorm_requests_per_second, s.http_max_retries, s.http_timeout_seconds)
        resolver = IngredientResolver(RxNormNormalizer(RxNavClient(s, rx), s.cache_dir), c.rx_concepts,
                                      c.ingredients, c.name_map, c.clock, concurrency=s.rxnorm_concurrency)
        dispatcher = AlertDispatcher(c.follows, c.alerts, c.users, c.clock)
        feed = ListFeeds(raw)
        run = await UpdateLabelsAndRecalls(feed, feed, c.labels, c.recalls, resolver, dispatcher,
                                           c.ingestion_runs, c.clock).execute()
        await rx.aclose()
        log.info("    %d labels loaded (%d skipped); drugs with an Rx label: %d -> %d of %d", run.records_loaded,
                 run.records_skipped, before, await label_coverage(c, targets), len(targets))

    log.info("3/4 signals (label match)")
    compute = ComputeQuarterSignals(c.reports, c.signals, c.labels, c.excluded_terms, c.clock)
    for quarter in sorted(await c.reports.quarters()):
        st = await compute.execute(quarter, RoleFilter.SUSPECT)
        log.info("    %s: %d signals, %d emerging", quarter, st.signals, st.emerging)
    matched = Counter(sig.label_match.value for sig in c.signals.all_items() if sig.is_signal)
    log.info("    label match of signals: %s", dict(matched))

    log.info("4/4 export")
    meta = export_dataset(c, data_dir)
    print(f"\nTotal size: {meta['total_megabytes']} MB, refreshed in {(time.monotonic() - started) / 60:.1f} min")


if __name__ == "__main__":
    asyncio.run(main())
