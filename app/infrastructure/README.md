# infrastructure - drivers and external services

Adapters that implement the ports.

## Tools used

- PyMongo async API (`AsyncMongoClient`), `IndexModel`
- redis-py asyncio (+ Sentinel)
- httpx (openFDA, RxNorm, DailyMed)
- APScheduler (daily jobs)

## Rules

- Implements `application/ports`; may import `domain` and `core`.
- Never imports `presentation`.
- Redis key strings are built only in `redis/key_schema.py`.
- Each MongoDB index lives in `mongodb/indexes.py` and must be justified with explain() before/after.

## Contents

| Item | Role |
|---|---|
| `database_container.py` | `STORAGE_BACKEND=databases`: wires the Mongo + Redis adapters |
| `mongodb/` | Client (w=majority), indexes, repositories, aggregation pipelines |
| `redis/` | Client (single node or Sentinel), key schema, stores (implemented) |
| `external/` | openFDA, RxNorm, DailyMed clients, bulk file feeds |
| `sync/` | Change-stream projector and resume-token checkpoint (run by `app/worker.py`) |
