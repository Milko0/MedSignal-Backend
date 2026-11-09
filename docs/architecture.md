# Architecture

## Layers

| Layer | Imports | Never imports |
|---|---|---|
| domain | nothing | everything else |
| application | domain, core | Motor, redis-py, httpx, FastAPI |
| infrastructure | application ports, domain, core | presentation |
| presentation | application, core | infrastructure (except in `dependencies.py`) |

## Read path: cache-aside (Drug 360)

```mermaid
sequenceDiagram
  participant V as Vue store
  participant A as GET /drugs/{rxcui}/overview
  participant R as Redis
  participant M as MongoDB
  V->>A: fetchDrug360
  A->>R: HGETALL shortage:{rxcui}
  alt miss
    A->>M: latest shortage status
    A->>R: HSET + EXPIRE (fill cache)
  end
  A->>R: SISMEMBER follows:{userId}
  A->>M: signals, label, recalls (secondary ok)
  A-->>V: Drug360Response (meta.disclaimer)
```

## Write path: event sync

```mermaid
flowchart LR
  I[Ingestion] -->|w=majority, _id = report id| M[(MongoDB)]
  M -->|change stream + resume token| W[Worker projector]
  W -->|recompute, then SET/HSET| R[(Redis)]
  W -->|event id| AL[Alerts, TTL 30 days]
```

Replays are safe: documents are upserted by id, Redis values are overwritten, alerts are keyed by event id.
If the resume token expires, `Reconcile` (FR-27) rebuilds Redis from MongoDB.
