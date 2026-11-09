# application - use cases, ports, DTOs

Orchestrates the domain through ports. One use case = one user-visible operation.

## Tools used

- Pydantic v2 (request/response DTOs, they become the Swagger schemas)
- `abc` (ports as abstract classes)

## Rules

- May import `domain` and `core` only.
- Never imports Motor, redis-py, httpx or FastAPI.
- Ports are named by purpose (`ShortageStatusStore`, `FollowStore`), not by technology.
- `GetDrug360` is the reference implementation of cache-aside; copy its style.

## Contents

| Item | Role |
|---|---|
| `ports/` | Abstract contracts for Mongo repositories, Redis stores, external sources, clock |
| `use_cases/` | auth, drugs, signals, shortages, cabinet, profile, ingestion, sync, admin |
| `services/alert_dispatcher.py` | Creates idempotent alerts for followers (FR-17, FR-30) |
| `dtos/` | Request/response models; responses carry `meta.disclaimer` |
