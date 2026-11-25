# scripts

Helper scripts, not part of the running service.

## Tools used

- Python 3.12
- httpx

## Rules

- `medsignal_api_check.py`: the data-source smoke test.
- `download_faers.py`: lists/downloads bulk partitions per quarter.

## Contents

| Item | Role |
|---|---|
| `medsignal_api_check.py` | Smoke test of all APIs |
| `download_faers.py` | FAERS manifest and download |
| `load_sample.py` | Sample loader (stub) |
| `benchmark_indexes.py` | `explain()` of the main queries with and without their index |
| `benchmark_cluster.py` | Read/write performance, staleness and failover tests on the MongoDB and Redis clusters (`docs/cap-theorem.md`) |
