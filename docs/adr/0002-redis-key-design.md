# ADR 0002: Redis key design

Status: accepted.

- `follows:{userId}` and `followers:{rxcui}` are SETs (many-to-many in both directions, no SCAN needed).
- Alerts: hash per alert (TTL 30 days) keyed by event id (replay-safe) plus a sorted-set index pruned on read.
- Counters are overwritten by recomputation from MongoDB; INCRBY is not used because a replay would double count.
