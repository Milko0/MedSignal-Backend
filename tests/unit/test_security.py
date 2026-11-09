from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_roundtrip():
    h = hash_password("s3cretpass")
    assert verify_password("s3cretpass", h) and not verify_password("wrong", h)


def test_token_roundtrip():
    assert decode_access_token(create_access_token("u1", "user"))["sub"] == "u1"
