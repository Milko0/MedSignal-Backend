"""Saves raw openFDA pages (shortages, NDC, labels, recalls) to JSON Lines for build_clean_dataset.py.

    python -m scripts.download_raw --out data/raw --ndc 20000 --labels 5000 --recalls 20000

FAERS reports come from the bulk partitions (scripts/download_faers.py), not from here.
Set OPENFDA_API_KEY in .env first (free key, much higher rate limits).
"""
import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings
from app.infrastructure.external.http import HttpFetcher
from app.infrastructure.external.openfda_client import OpenFdaFeeds


async def dump(path: Path, source) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        async for rec in source:
            f.write(json.dumps(rec) + "\n")
            n += 1
    return n


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--ndc", type=int, default=20000)
    ap.add_argument("--labels", type=int, default=5000)
    ap.add_argument("--recalls", type=int, default=20000)
    a = ap.parse_args()
    s = get_settings()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    feeds = OpenFdaFeeds(s, HttpFetcher(s.openfda_requests_per_second, s.http_max_retries, s.http_timeout_seconds))
    print("shortages", await dump(out / "shortages.jsonl", feeds.fetch_shortages()))
    print("ndc", await dump(out / "ndc.jsonl", feeds.fetch_products(a.ndc)))
    print("labels", await dump(out / "labels.jsonl", feeds.fetch_labels(a.labels)))
    print("recalls", await dump(out / "recalls.jsonl", feeds.fetch_recalls(a.recalls)))


if __name__ == "__main__":
    asyncio.run(main())
