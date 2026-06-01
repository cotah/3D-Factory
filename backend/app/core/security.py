"""Security helpers: password hashing (bcrypt) and JWT tokens (PyJWT).

We use the ``bcrypt`` library directly instead of passlib to avoid a known
compatibility issue between recent bcrypt releases and passlib 1.7.x.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only accepts up to 72 bytes of input.
_BCRYPT_MAX_BYTES = 72

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ----------------------------- Passwords -----------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password and return the hash as a string."""
    pwd_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Check a plaintext password against a stored hash."""
    try:
        pwd_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ------------------------------- JWT ---------------------------------
def _create_token(subject: str | int, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int) -> str:
    return _create_token(
        subject,
        TOKEN_TYPE_ACCESS,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject,
        TOKEN_TYPE_REFRESH,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jwt.PyJWTError`` if invalid/expired."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
