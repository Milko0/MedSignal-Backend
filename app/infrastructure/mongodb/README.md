# infrastructure/mongodb

Document DB access. Collections: `reports`, `labels`, `shortages`, `signals`, `recalls`, `drugs`, `users`, `excluded_terms`, `ingestion_runs`, `sync_checkpoints`.

## Tools used

- MongoDB 7, 3-member replica set (NFR-02)
- Motor 3.x
- Aggregation pipelines (`pipelines/`)

## Rules

- Writes use `w=majority` (NFR-03).
- Heavy reads can use secondaries via `get_collection(..., secondary_ok=True)`.
- Put `$match` before `$unwind` in the pair pipeline.
- Sharding candidate: hashed key on drug code or report id (NFR-07).

## Contents

| Item | Role |
|---|---|
| `client.py` | Motor client factory |
| `indexes.py` | All indexes |
| `repositories/` | One adapter per port (methods raise NotImplementedError) |
| `pipelines/signal_counts.py` | Pipeline 1 (pair counts) |
| `pipelines/pair_counts.py` | Pipeline 2 (stub) |
| `pipelines/stats_by_group.py` | Pipeline 3 (stub) |
