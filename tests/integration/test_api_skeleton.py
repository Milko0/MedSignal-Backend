from fastapi.testclient import TestClient

from app.main import app


def test_openapi_lists_core_endpoints():
    with TestClient(app) as c:
        paths = c.get("/openapi.json").json()["paths"]
        for p in ("/api/drugs/{rxcui}/overview", "/api/signals", "/api/cabinet/follows",
                  "/api/shortages/{rxcui}/alternatives", "/api/admin/ingestion/faers"):
            assert p in paths


def test_admin_requires_auth():
    with TestClient(app) as c:
        assert c.get("/api/admin/ingestion/runs").status_code == 401
