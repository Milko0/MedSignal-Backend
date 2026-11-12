# infrastructure/redis

Key-value DB access. Self-hosted Redis (docker locally, VMs on the UNIPI Virtual Lab): no managed service.

## Tools used

- Redis 7 with AOF persistence
- redis-py asyncio client
- Redis Sentinel for failover (primary + 2 replicas)

## Rules

- Single node for development (`REDIS_URL`), Sentinel when `REDIS_SENTINELS` is set.
- Counters are written with SET after recomputation, never INCRBY (replays would double count).
- Follows and alerts exist only in Redis: keep AOF on.

## Contents

| Item | Role |
|---|---|
| `key_schema.py` | shortage:{rxcui}, follows:{userId}, followers:{rxcui}, alert:{userId}:{eventId}, alerts:{userId}, count:{rxcui}:{reaction}:{quarter}, revoked:{jti} (logout, TTL = token's remaining life) |
| `client.py` | Client factory |
| `stores/` | ShortageStatus, Follow, Alert, Counter, RevokedToken stores (implemented) |
