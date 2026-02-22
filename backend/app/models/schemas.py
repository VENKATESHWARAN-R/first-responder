"""Pydantic schemas for request/response models."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    message: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    allowed_namespaces: list[str]
    theme_pref: str


# ── Admin ─────────────────────────────────────────────────────────────
class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "viewer"
    allowed_namespaces: list[str] = []


class UpdateUserRequest(BaseModel):
    role: str | None = None
    allowed_namespaces: list[str] | None = None
    password: str | None = None


class ThemeUpdateRequest(BaseModel):
    theme_pref: str


# ── Kubernetes ────────────────────────────────────────────────────────
class NamespaceSummary(BaseModel):
    name: str
    health: str  # Healthy / Degraded / Critical
    deployments_ready: int
    deployments_total: int
    pods_running: int
    pods_pending: int
    pods_failed: int
    pods_total: int
    top_restart_count: int
    warning_events: int
    last_refreshed: str


class WorkloadSummary(BaseModel):
    kind: str
    name: str
    namespace: str
    desired: int
    ready: int
    available: int
    images: list[str]
    conditions: list[dict]


class PodSummary(BaseModel):
    name: str
    namespace: str
    phase: str
    node: str | None
    start_time: str | None
    restart_count: int
    containers: list[dict]


class PodDetail(BaseModel):
    name: str
    namespace: str
    phase: str
    node: str | None
    start_time: str | None
    restart_count: int
    containers: list[dict]
    events: list[dict]
    likely_causes: list[dict]


class EventItem(BaseModel):
    type: str
    reason: str
    message: str
    source: str
    first_seen: str | None
    last_seen: str | None
    count: int
    involved_object: str


class ConfigItem(BaseModel):
    kind: str
    name: str
    namespace: str
