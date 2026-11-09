from fastapi.testclient import TestClient

from app.main import app


def test_openapi_lists_core_endpoints():
    with TestClient(app) as c:
        paths = c.get("/openapi.json").json()["paths"]
        for p in ("/api/v1/drugs/{rxcui}/overview", "/api/v1/signals", "/api/v1/cabinet/follows",
                  "/api/v1/shortages/{rxcui}/alternatives", "/api/v1/admin/ingestion/faers"):
            assert p in paths


def test_endpoints_return_501_until_implemented():
    with TestClient(app) as c:
        assert c.get("/api/v1/signals").status_code == 501


def test_admin_requires_auth():
    with TestClient(app) as c:
        assert c.get("/api/v1/admin/ingestion/runs").status_code == 401
