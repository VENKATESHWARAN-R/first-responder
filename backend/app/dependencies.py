"""FastAPI dependencies — auth guards, current user extraction."""

from __future__ import annotations

from fastapi import Cookie, HTTPException, status

from app.services.auth import decode_access_token, get_user_by_id


def get_current_user(session_token: str | None = Cookie(default=None)) -> dict:
    """Extract and validate the current user from the session cookie."""
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user_id = decode_access_token(session_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_admin(user: dict = None) -> dict:
    """Verify the user has admin role."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
