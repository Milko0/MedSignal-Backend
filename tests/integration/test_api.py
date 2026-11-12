import pytest
from fastapi.testclient import TestClient

from app.core.constants import API_PREFIX, DISCLAIMER
from app.main import create_app
from tests.fixtures.raw import IBU, NAP

P = API_PREFIX


@pytest.fixture
def client(world):
    app = create_app()
    app.state.container = world            # no lifespan: the container is injected
    return TestClient(app)


def _login(client, name="ana"):
    client.post(f"{P}/auth/register", json={"username": name, "email": f"{name}@example.com", "password": "password123"})
    token = client.post(f"{P}/auth/login", json={"identifier": name, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_openapi(client):
    h = client.get(f"{P}/health").json()
    assert h["status"] == "ok" and h["reports"] == 401
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/drugs", "/drugs/{rxcui}/overview", "/signals", "/signals/emerging", "/statistics",
              "/shortages/{rxcui}/alternatives", "/cabinet/follows", "/admin/ingestion/runs", "/profile/alert-settings"):
        assert f"{P}{p}" in paths


def test_search_is_typo_tolerant(client):
    r = client.get(f"{P}/drugs", params={"query": "ibuprofin"}).json()
    assert r[0]["rxcui"] == IBU and r[0]["score"] >= 0.75
    assert client.get(f"{P}/drugs", params={"query": "x"}).status_code == 422


def test_signals_carry_the_disclaimer_and_numbers(client):
    body = client.get(f"{P}/signals", params={"quarter": "2026Q2", "min_reports": 1}).json()
    assert body["meta"]["disclaimer"] == DISCLAIMER
    row = body["data"]["items"][0]
    assert (row["a"], row["b"], row["c"], row["d"]) == (20, 20, 4, 156) and row["is_emerging"]
    assert body["data"]["match_coverage"] > 0.99
    gaps = client.get(f"{P}/drugs/{IBU}/label-gaps").json()
    assert gaps["meta"]["disclaimer"] == DISCLAIMER and gaps["data"]["gaps"][0]["match_level"] == "PARTIAL"
    reports = client.get(f"{P}/signals/{IBU}/gastrointestinal haemorrhage/reports", params={"limit": 5}).json()
    assert reports["total"] == 31 and len(reports["items"]) == 5


def test_drug_360_shortage_and_alternatives(client):
    o = client.get(f"{P}/drugs/{NAP}/overview").json()
    assert o["shortage"]["status"] == "CURRENT" and o["recalls"]["class_ii"] == 1 and o["recalls"]["linked_share"] == 0.5
    alt = client.get(f"{P}/shortages/{NAP}/alternatives").json()
    assert [a["match_type"] for a in alt["items"]] == ["SAME_INGREDIENT", "SAME_CLASS"]
    assert client.get(f"{P}/drugs/0/overview").status_code == 404
    st = client.get(f"{P}/statistics", params={"group_by": "sex", "rxcui": IBU}).json()
    assert {b["group"] for b in st["buckets"]} <= {"MALE", "FEMALE", "UNKNOWN"}
    assert client.get(f"{P}/statistics", params={"group_by": "nope"}).status_code == 422


def test_auth_cabinet_and_alerts_flow(client):
    assert client.get(f"{P}/cabinet").status_code == 401
    h = _login(client)
    assert client.post(f"{P}/auth/register", json={"username": "ana", "email": "ana@example.com", "password": "password123"}).status_code == 409
    assert client.post(f"{P}/auth/login", json={"identifier": "ana", "password": "wrongpass1"}).status_code == 401
    assert client.post(f"{P}/cabinet/follows", json={"rxcui": NAP}, headers=h).status_code == 204
    assert client.post(f"{P}/cabinet/follows", json={"rxcui": "0"}, headers=h).status_code == 404
    cab = client.get(f"{P}/cabinet", headers=h).json()
    assert cab == [{"rxcui": NAP, "name": "NAPROXEN", "shortage_status": "CURRENT", "packages_in_shortage": 1}]
    assert client.get(f"{P}/drugs/{NAP}/overview", headers=h).json()["is_followed"] is True
    assert client.get(f"{P}/cabinet/alerts", headers=h).json() == []
    assert client.delete(f"{P}/cabinet/follows/{NAP}", headers=h).status_code == 204
    assert client.get(f"{P}/cabinet", headers=h).json() == []


def test_profile_and_admin_roles(client, world):
    h = _login(client, "bob")
    assert client.get(f"{P}/profile", headers=h).json()["username"] == "bob"
    s = client.put(f"{P}/profile/alert-settings", headers=h, json={"new_signal": False, "label_updated": True, "shortage_changed": True, "new_recall": True, "min_reports": 30}).json()
    assert s["new_signal"] is False and client.get(f"{P}/profile/alert-settings", headers=h).json()["min_reports"] == 30
    assert client.post(f"{P}/profile/password", headers=h, json={"current_password": "password123", "new_password": "newpassword9"}).status_code == 204
    assert client.get(f"{P}/admin/excluded-terms", headers=h).status_code == 403          # user is not admin
    assert client.get(f"{P}/admin/ingestion/runs").status_code == 401
    from app.core.config import get_settings
    from app.core.security import create_access_token
    admin = {"Authorization": "Bearer " + create_access_token(get_settings(), "admin-1", "admin")}
    assert {t["term"] for t in client.get(f"{P}/admin/excluded-terms", headers=admin).json()} == {"DRUG INEFFECTIVE", "OFF LABEL USE"}
    assert client.post(f"{P}/admin/excluded-terms", headers=admin, json={"term": "product use issue"}).json()["term"] == "PRODUCT USE ISSUE"
    assert client.delete(f"{P}/admin/excluded-terms/product use issue", headers=admin).status_code == 204
    runs = client.get(f"{P}/admin/ingestion/runs", headers=admin).json()
    assert {r["type"] for r in runs} >= {"FULL_LOAD", "SHORTAGE_POLL", "INCREMENTAL"} and runs[0]["stats"] is not None
    assert client.get(f"{P}/admin/reports", headers=admin).status_code == 501              # CRUD still a stub
    assert client.post(f"{P}/admin/reconciliation", headers=admin).json()["ingredients_checked"] >= 1
    assert client.delete(f"{P}/profile", headers=h).status_code == 204
