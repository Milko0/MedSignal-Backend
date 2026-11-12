"""Password hashing and JWT helpers (NFR-10)."""
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(settings: Settings, user_id: str, role: str) -> str:
    """Claims: sub, role, iat, exp and a unique jti (the id a logout revokes)."""
    now = datetime.now(UTC)
    claims = {"sub": user_id, "role": role, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
              "jti": uuid.uuid4().hex}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> dict:
    """Raises jwt.PyJWTError when the token is invalid, expired or misses a required claim."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                      options={"require": ["sub", "exp", "jti"]})
