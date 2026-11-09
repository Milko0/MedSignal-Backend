# infrastructure - drivers and external services

Adapters that implement the ports.

## Tools used

- Motor (async MongoDB driver) / PyMongo `IndexModel`
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
| `mongodb/` | Client (w=majority), indexes, repositories (stubs), aggregation pipelines |
| `redis/` | Client (single node or Sentinel), key schema, stores (implemented) |
| `external/` | openFDA, RxNorm, DailyMed clients (stubs with endpoint notes) |
| `sync/` | Change-stream projector and resume-token checkpoint |
| `scheduling/jobs.py` | Daily shortage poll (FR-28) |
