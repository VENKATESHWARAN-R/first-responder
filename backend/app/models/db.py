from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    admin = 'admin'
    viewer = 'viewer'


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.viewer)
    allowed_namespaces: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    theme_pref: str = Field(default='minimal')
    created_at: datetime = Field(default_factory=datetime.utcnow)
