"""Authentication helpers: JWT creation/verification, password hashing."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import hashlib
import hmac
import secrets

import jwt

from app.config import settings
from app.database import get_db


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 + salt (simple, avoids bcrypt compat issues)."""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        salt, stored_hash = hashed.split("$", 1)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return hmac.compare_digest(h, stored_hash)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Return user_id or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return int(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)


def list_users() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]


def create_user(email: str, password: str, role: str, allowed_namespaces: list[str]) -> dict:
    pw_hash = hash_password(password)
    ns_json = json.dumps(allowed_namespaces)
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, role, allowed_namespaces) VALUES (?, ?, ?, ?)",
            (email, pw_hash, role, ns_json),
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid)  # type: ignore[arg-type]


def update_user(user_id: int, role: str | None, allowed_namespaces: list[str] | None, password: str | None) -> dict | None:
    with get_db() as conn:
        parts: list[str] = []
        params: list = []
        if role is not None:
            parts.append("role = ?")
            params.append(role)
        if allowed_namespaces is not None:
            parts.append("allowed_namespaces = ?")
            params.append(json.dumps(allowed_namespaces))
        if password is not None:
            parts.append("password_hash = ?")
            params.append(hash_password(password))
        if not parts:
            return get_user_by_id(user_id)
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(parts)} WHERE id = ?", params)
        conn.commit()
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def update_theme(user_id: int, theme_pref: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE users SET theme_pref = ? WHERE id = ?", (theme_pref, user_id))
        conn.commit()


def add_audit_log(user_id: int | None, event: str, detail: str | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id, event, detail) VALUES (?, ?, ?)",
            (user_id, event, detail),
        )
        conn.commit()


def filter_namespaces(user_namespaces: list[str], available: list[str]) -> list[str]:
    """Filter available namespaces based on user's allowed list.

    If user has ["*"], they can see all namespaces.
    Otherwise, return the intersection.
    """
    if "*" in user_namespaces:
        return available
    return [ns for ns in available if ns in user_namespaces]


def _row_to_dict(row) -> dict:
    d = dict(row)
    if "allowed_namespaces" in d and isinstance(d["allowed_namespaces"], str):
        d["allowed_namespaces"] = json.loads(d["allowed_namespaces"])
    return d
