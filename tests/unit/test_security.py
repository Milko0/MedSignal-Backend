from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password

SETTINGS = Settings(jwt_secret="test-secret-at-least-32-characters-long")


def test_password_roundtrip():
    h = hash_password("s3cretpass")
    assert verify_password("s3cretpass", h) and not verify_password("wrong", h)


def test_token_roundtrip():
    claims = decode_access_token(SETTINGS, create_access_token(SETTINGS, "u1", "user"))
    assert claims["sub"] == "u1" and claims["role"] == "user"
