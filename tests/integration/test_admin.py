"""Admin area: CRUD on reports, labels, shortages, users (FR-22 to FR-25) and ingestion triggers (FR-19, FR-20)."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.constants import API_PREFIX
from app.core.security import create_access_token
from app.domain.entities.enums import RunType
from app.infrastructure.ingestion_jobs import IngestionJobs
from app.main import create_app
from tests.fixtures.raw import IBU

P = f"{API_PREFIX}/admin"


class FakeJobs(IngestionJobs):
    """The real guard and file checks; the jobs only record their arguments (no openFDA, no RxNav)."""

    def __init__(self, c, settings):
        super().__init__(c, settings)
        self.calls = []

    async def incremental(self, label_limit):
        self.calls.append(("incremental", label_limit))
        self.running.discard("incremental")

    async def faers(self, paths, window_quarters):
        self.calls.append(("faers", paths, window_quarters))
        self.running.discard("faers")


@pytest.fixture
def setup(world, tmp_path):
    settings = get_settings().model_copy(update={"faers_dir": str(tmp_path)})
    (tmp_path / "2026q3-drug-event-0001-of-0031.json.zip").write_bytes(b"x")
    app = create_app()
    app.state.container = world
    app.state.ingestion_jobs = FakeJobs(world, settings)
    admin = {"Authorization": "Bearer " + create_access_token(get_settings(), "admin-1", "admin")}
    return TestClient(app), admin, app.state.ingestion_jobs, world


def test_admin_routes_need_the_admin_role(setup):
    client, _, _, _ = setup
    user = {"Authorization": "Bearer " + create_access_token(get_settings(), "u-1", "user")}
    for path in ("/reports", "/labels", "/shortages", "/users"):
        assert client.get(P + path).status_code == 401
        assert client.get(P + path, headers=user).status_code == 403


def test_report_crud(setup):
    client, admin, _, _ = setup
    page = client.get(f"{P}/reports", headers=admin, params={"page_size": 3}).json()
    assert len(page) == 3 and page[0]["receive_date"] >= page[-1]["receive_date"]          # newest first
    report = client.get(f"{P}/reports/{page[0]['report_id']}", headers=admin).json()
    assert client.post(f"{P}/reports", headers=admin, json=report).status_code == 409
    new = {**report, "report_id": "999", "version": 1}
    assert client.post(f"{P}/reports", headers=admin, json=new).status_code == 201
    new["country"] = "IT"
    assert client.put(f"{P}/reports/999", headers=admin, json=new).json()["country"] == "IT"
    assert client.put(f"{P}/reports/998", headers=admin, json=new).status_code == 422       # id mismatch
    assert client.delete(f"{P}/reports/999", headers=admin).status_code == 204
    assert client.get(f"{P}/reports/999", headers=admin).status_code == 404


def test_label_crud(setup):
    client, admin, _, _ = setup
    labels = client.get(f"{P}/labels", headers=admin).json()
    assert labels and labels == sorted(labels, key=lambda lb: lb["set_id"])
    label = {**labels[0], "set_id": "ABC-1", "has_boxed_warning": True}
    assert client.post(f"{P}/labels", headers=admin, json=label).json()["set_id"] == "abc-1"   # stored lower case
    assert client.get(f"{P}/labels/ABC-1", headers=admin).json()["has_boxed_warning"] is True
    assert client.delete(f"{P}/labels/abc-1", headers=admin).status_code == 204
    assert client.delete(f"{P}/labels/abc-1", headers=admin).status_code == 404


def test_shortage_crud_refreshes_the_cached_status(setup):
    client, admin, _, _ = setup
    record = {"package_ndc": "0000-0000-01", "status": "CURRENT", "ingredient_rxcuis": [IBU]}
    before = client.get(f"{API_PREFIX}/drugs/{IBU}/overview").json()["shortage"]["packages_in_shortage"]   # cached
    assert client.post(f"{P}/shortages", headers=admin, json=record).status_code == 201
    after = client.get(f"{API_PREFIX}/drugs/{IBU}/overview").json()["shortage"]
    assert after["packages_in_shortage"] == before + 1 and after["status"] == "CURRENT"
    record["status"] = "RESOLVED"
    assert client.put(f"{P}/shortages/0000-0000-01", headers=admin, json=record).json()["status"] == "RESOLVED"
    assert client.delete(f"{P}/shortages/0000-0000-01", headers=admin).status_code == 204
    assert client.get(f"{API_PREFIX}/drugs/{IBU}/overview").json()["shortage"]["packages_in_shortage"] == before


def test_user_crud_never_returns_passwords(setup):
    client, admin, _, world = setup
    body = {"username": "luca", "email": "Luca@Example.com", "password": "password123", "role": "user"}
    created = client.post(f"{P}/users", headers=admin, json=body).json()
    assert created["email"] == "luca@example.com" and "password" not in created and "password_hash" not in created
    assert client.post(f"{P}/users", headers=admin, json={**body, "email": "x@example.com"}).status_code == 409
    uid = created["user_id"]
    assert client.put(f"{P}/users/{uid}", headers=admin, json={"role": "admin"}).json()["role"] == "admin"
    assert client.put(f"{P}/users/{uid}", headers=admin, json={"password": "newpassword1"}).status_code == 200
    login = client.post(f"{API_PREFIX}/auth/login", json={"identifier": "luca", "password": "newpassword1"})
    assert login.status_code == 200
    asyncio.run(world.follows.follow(uid, IBU))
    assert client.delete(f"{P}/users/{uid}", headers=admin).status_code == 204
    assert asyncio.run(world.follows.followers(IBU)) == set()                     # follows removed with the user
    assert client.get(f"{P}/users/{uid}", headers=admin).status_code == 404


def test_ingestion_triggers_start_in_the_background(setup):
    client, admin, jobs, _ = setup
    r = client.post(f"{P}/ingestion/incremental", headers=admin, params={"label_limit": 50})
    assert r.status_code == 202 and r.json()["job"] == "incremental"
    r = client.post(f"{P}/ingestion/faers", headers=admin, json={"files": ["2026q3-drug-event-0001-of-0031.json.zip"]})
    assert r.status_code == 202
    assert jobs.calls[0] == ("incremental", 50) and jobs.calls[1][0] == "faers" and jobs.calls[1][2] is None


def test_faers_trigger_rejects_paths_and_missing_files(setup):
    client, admin, jobs, _ = setup
    for name in ("../secret.txt", "missing.json.zip"):
        assert client.post(f"{P}/ingestion/faers", headers=admin, json={"files": [name]}).status_code == 422
    assert jobs.calls == []


def test_a_second_job_of_the_same_kind_is_refused(setup):
    client, admin, jobs, _ = setup
    jobs.running.add("incremental")                         # a job is still running
    assert client.post(f"{P}/ingestion/incremental", headers=admin).status_code == 409


async def test_a_crashing_job_is_logged(world):
    jobs = IngestionJobs(world, get_settings())

    async def boom():
        raise RuntimeError("openFDA is down")

    jobs.start("incremental")
    await jobs._guard("incremental", RunType.INCREMENTAL, "openfda", boom)
    failed = [r for r in await world.ingestion_runs.list(0, 100) if r.errors]
    assert [r.errors for r in failed] == [["RuntimeError: openFDA is down"]] and "incremental" not in jobs.running
