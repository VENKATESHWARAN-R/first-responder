"""SQLite database setup and helpers for user/session management."""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.config import settings


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def get_db_path() -> str:
    return settings.db_path


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row_factory set."""
    path = get_db_path()
    _ensure_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and seed admin user if not present."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                allowed_namespaces TEXT NOT NULL DEFAULT '[]',
                theme_pref TEXT NOT NULL DEFAULT 'minimal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event TEXT NOT NULL,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Seed admin user if not exists
        from app.services.auth import hash_password

        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (settings.admin_email,)
        ).fetchone()
        if not row:
            pw_hash = hash_password(settings.admin_password)
            conn.execute(
                "INSERT INTO users (email, password_hash, role, allowed_namespaces) VALUES (?, ?, ?, ?)",
                (settings.admin_email, pw_hash, "admin", '["*"]'),
            )
            conn.commit()
