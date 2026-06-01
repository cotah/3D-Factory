"""Shared FastAPI dependencies (authentication and authorization)."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.models import User, UserRole

# tokenUrl is only used by the Swagger "Authorize" button; the scheme simply
# extracts the bearer token from the Authorization header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from a Bearer access token.

    1. Decode the JWT from the Authorization header.
    2. Ensure it is an *access* token (not a refresh token).
    3. Load the user by the token subject (``sub`` = user id).
    4. Return the active user or raise 401.
    """
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _credentials_exception

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise _credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise _credentials_exception

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _credentials_exception

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_exception

    return user


def require_roles(*roles: UserRole):
    """Dependency factory restricting access to the given roles."""

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _checker
