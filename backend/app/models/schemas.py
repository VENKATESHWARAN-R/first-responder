from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.models.db import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    allowed_namespaces: list[str]
    theme_pref: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.viewer
    allowed_namespaces: list[str] = []


class UserUpdate(BaseModel):
    role: UserRole | None = None
    allowed_namespaces: list[str] | None = None
    theme_pref: Literal['minimal', 'neo-brutal'] | None = None


class NamespaceSummary(BaseModel):
    namespace: str
    health: Literal['Healthy', 'Degraded', 'Critical']
    deployments: str
    pods: dict[str, int]
    top_restart_count: int
    last_refreshed: datetime
