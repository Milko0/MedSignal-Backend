# infrastructure/mongodb

Document DB adapters. Collections: `reports`, `signals`, `ingredients`, `rx_concepts`, `products`, `labels`, `shortages`,
`shortage_events`, `recalls`, `name_map`, `users`, `excluded_terms`, `ingestion_runs`, `sync_checkpoints`.

## Tools used

- MongoDB 7+ (3-member replica set on the cluster, NFR-02); a single `mongod` works for development
- PyMongo native async API (`AsyncMongoClient`)
- Aggregation pipelines (`pipelines/`)

## Rules

- Writes use `w=majority` (NFR-03); heavy reads can use secondaries via `get_collection(..., secondary_ok=True)`.
- `_id` is the natural id of the model (`documents.py`); upserts are idempotent.
- Every index is in `indexes.py` with the query it serves; check it with `scripts/benchmark_indexes.py`.
- Sharding candidate for `reports`: hashed `report_id` (NFR-07).

## Contents

| Item | Role |
|---|---|
| `client.py` | Client factory |
| `documents.py` | Model <-> document mapping, bulk upserts |
| `indexes.py` | All indexes, created at start-up (`ensure_indexes`) |
| `repositories/` | One adapter per repository port |
| `pipelines/signal_counts.py` | Pair counts, top reactions, monthly trend |
| `pipelines/stats_by_group.py` | Report counts by age group, sex, country, seriousness, type, quarter |
