"""Loads the clean dataset (data/clean/*.jsonl) into MongoDB, through the same ports the API uses.

    py scripts/seed_databases.py              # upsert into MONGO_URI / MONGO_DB (safe to re-run)
    py scripts/seed_databases.py --drop       # empty the dataset collections first (users and follows are kept)

Takes a few minutes for ~130k reports. Redis needs no seeding: follows, alerts and revoked tokens are created by
the users; shortage summaries and counters are rebuilt from MongoDB (worker / Reconcile).
"""
import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.infrastructure.database_container import build_database_container
from app.infrastructure.memory.dataset import FILES, load_dataset

DATASET_COLLECTIONS = [*(attr for _, attr in FILES.values()), "shortage_events", "sync_checkpoints"]
log = logging.getLogger("seed")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=None, help="default: DATA_DIR (data/clean)")
    ap.add_argument("--drop", action="store_true", help="empty the dataset collections before loading")
    ap.add_argument("--batch-size", type=int, default=5000)
    args = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    s = get_settings()
    data_dir = args.data_dir or s.data_dir
    if not Path(data_dir, "reports.jsonl").exists():
        sys.exit(f"No dataset in {data_dir}: build it (scripts/build_clean_dataset.py) or unzip the shared copy.")
    c = await build_database_container(s)
    db = c.reports.col.database
    if args.drop:
        for name in DATASET_COLLECTIONS:
            await db.drop_collection(name)
        log.info("Dropped %s", ", ".join(DATASET_COLLECTIONS))
        c = await build_database_container(s)                   # recreate indexes and default excluded terms
    t0 = time.monotonic()
    log.info("Loading %s into %s/%s ...", data_dir, s.mongo_uri, s.mongo_db)
    counts = await load_dataset(c, data_dir, args.batch_size)
    for name, n in counts.items():
        log.info("  %-24s %8d", name, n)
    log.info("Done in %.1f min. Collections now:", (time.monotonic() - t0) / 60)
    for name in sorted(await db.list_collection_names()):
        stats = await db.command("collStats", name)
        log.info("  %-18s %8d docs %8.1f MB data %6.1f MB indexes", name, stats["count"], stats["size"] / 1e6,
                 stats["totalIndexSize"] / 1e6)


if __name__ == "__main__":
    asyncio.run(main())
