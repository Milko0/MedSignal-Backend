"""Builds data/clean/*.jsonl from raw exports (phase 3 of the plan).

    python -m scripts.build_clean_dataset --raw-dir data/raw --faers "data/faers/*.json" --out data/clean [--link-recalls]

Needs network for RxNav the first time; every answer is cached in CACHE_DIR, so the second run is offline.
Prints the build report and the size of the dataset (the brief asks for at least 50-100 MB).
"""
import argparse
import asyncio
import glob
import json

from app.application.services.alert_dispatcher import AlertDispatcher
from app.application.services.ingredient_resolver import IngredientResolver
from app.application.use_cases.ingestion.build_clean_dataset import BuildCleanDataset
from app.core.config import get_settings
from app.domain.entities.excluded_term import ExcludedTerm
from app.infrastructure.external.file_feeds import FileFeeds
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.rxnorm_client import RxNavClient
from app.infrastructure.external.rxnorm_normalizer import RxNormNormalizer
from app.infrastructure.memory.dataset import export_dataset
from app.infrastructure.memory.factory import (
    DEFAULT_EXCLUDED_TERMS,
    build_memory_container,
)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--faers", nargs="+", required=True, help="FAERS partition files (globs allowed)")
    ap.add_argument("--out", default="data/clean")
    ap.add_argument("--link-recalls", action="store_true", help="propose drug candidates for recalls without ids")
    ap.add_argument("--min-a", type=int, default=3, help="store signal pairs with at least this many reports")
    a = ap.parse_args()

    s = get_settings()
    paths = sorted(p for pattern in a.faers for p in glob.glob(pattern))
    if not paths:
        raise SystemExit("No FAERS files matched --faers")

    c = build_memory_container()
    for term in DEFAULT_EXCLUDED_TERMS:
        await c.excluded_terms.add(ExcludedTerm(term=term, added_at=c.clock.now()))

    rx = HttpFetcher(s.rxnorm_requests_per_second, s.http_max_retries, s.http_timeout_seconds)
    normalizer = RxNormNormalizer(RxNavClient(s, rx), s.cache_dir)
    resolver = IngredientResolver(normalizer, c.rx_concepts, c.ingredients, c.name_map, c.clock)
    feeds = FileFeeds(a.raw_dir)
    dispatcher = AlertDispatcher(c.follows, c.alerts, c.users, c.clock)

    builder = BuildCleanDataset(c, resolver, feeds, feeds, feeds, feeds, feeds, normalizer, dispatcher)
    report = await builder.execute(paths, link_recalls=a.link_recalls, min_a=a.min_a)
    meta = export_dataset(c, a.out)
    print(json.dumps({"build": report.__dict__, "dataset": meta}, indent=1, default=str))
    print(f"\nTotal size: {meta['total_megabytes']} MB")


if __name__ == "__main__":
    asyncio.run(main())
