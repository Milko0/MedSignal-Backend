# tests

Automated tests.

## Tools used

- pytest, pytest-asyncio
- FastAPI TestClient (httpx)

## Rules

- `unit/`: domain and key schema, no I/O.
- `integration/`: API against the app object.
- `e2e/`: with the docker compose databases (to be written).

## Contents

| Item | Role |
|---|---|
| `unit/test_signal_calculator.py` | Reproduces PRR 4.87 / CI 4.48 for ibuprofen + GI haemorrhage |
| `integration/test_api_skeleton.py` | OpenAPI paths, 501 stubs, auth on admin |
