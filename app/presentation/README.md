# presentation - FastAPI delivery layer

HTTP only: parse, authenticate, call a use case, return a DTO.

## Tools used

- FastAPI + Uvicorn (Swagger UI at `/docs`, OpenAPI at `/openapi.json`)
- Pydantic v2 validation
- HTTP Bearer + JWT (guest, user, admin roles)

## Rules

- No business logic in routers.
- Imports `application` DTOs/use cases; concrete adapters are wired only in `dependencies.py`.
- Every signal / label-gap response includes `meta.disclaimer` (NFR-11).
- Admin functions (FR-19 to FR-27) are exposed through `/docs`; there is no admin screen.

## Contents

| Item | Role |
|---|---|
| `api/v1/router.py` | Aggregates routers |
| `api/v1/routers/` | health, auth, drugs, signals, statistics, shortages, cabinet, profile, admin/ |
| `api/v1/dependencies.py` | DB handles, auth, roles, use-case wiring example |
| `api/v1/error_handlers.py` | Domain exceptions to HTTP codes |
