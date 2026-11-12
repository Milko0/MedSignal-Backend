from app.infrastructure.redis import key_schema as k


def test_keys():
    assert k.shortage("5640") == "shortage:5640"
    assert k.follows("u1") == "follows:u1"
    assert k.followers("5640") == "followers:5640"
    assert k.alert("u1", "e9") == "alert:u1:e9"
    assert k.counter("5640", "NAUSEA", "2026Q3") == "count:5640:NAUSEA:2026Q3"
    assert k.revoked_token("abc") == "revoked:abc"
