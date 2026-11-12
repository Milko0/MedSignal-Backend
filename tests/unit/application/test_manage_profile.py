from datetime import UTC, datetime

from app.application.use_cases.profile.manage_profile import ManageProfile
from app.domain.entities.alert import Alert
from app.domain.entities.enums import AlertType
from app.domain.entities.user import User
from app.infrastructure.clock import FixedClock
from app.infrastructure.memory.factory import build_memory_container

NOW = datetime(2026, 11, 10, tzinfo=UTC)


async def test_delete_account_removes_follows_and_alerts():
    c = build_memory_container(FixedClock(NOW))
    await c.users.create(User(user_id="u1", username="ana", email="ana@x.com", password_hash="h"))
    await c.follows.follow("u1", "1")
    await c.follows.follow("u2", "1")
    await c.alerts.add(Alert(alert_id="a", user_id="u1", type=AlertType.SIGNAL, drug_rxcui="1", message="m",
                             created_at=NOW), 60)
    await ManageProfile(c.users, c.follows, c.alerts).delete("u1")
    assert await c.users.get_by_id("u1") is None
    assert await c.follows.followers("1") == {"u2"} and await c.follows.list_followed("u1") == set()
    assert await c.alerts.list("u1") == []
