"""API contract tests for authentication endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

# Use a temporary database for tests
os.environ["NSO_DB_PATH"] = "/tmp/test_nso.db"
os.environ["NSO_ADMIN_EMAIL"] = "testadmin@test.com"
os.environ["NSO_ADMIN_PASSWORD"] = "testpass123"
os.environ["NSO_SECRET_KEY"] = "test-secret-key-not-for-prod"

# Remove test DB if it exists
if os.path.exists("/tmp/test_nso.db"):
    os.remove("/tmp/test_nso.db")

from app.database import init_db
from app.main import app

init_db()

def _make_client() -> TestClient:
    """Create a fresh TestClient (no shared cookies)."""
    return TestClient(app, cookies={})


class TestHealthEndpoint:
    def test_health_check(self):
        c = _make_client()
        response = c.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthEndpoints:
    def test_login_success(self):
        c = _make_client()
        response = c.post(
            "/api/auth/login",
            json={"email": "testadmin@test.com", "password": "testpass123"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Login successful"
        assert "session_token" in response.cookies

    def test_login_wrong_password(self):
        c = _make_client()
        response = c.post(
            "/api/auth/login",
            json={"email": "testadmin@test.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self):
        c = _make_client()
        response = c.post(
            "/api/auth/login",
            json={"email": "nobody@test.com", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_me_unauthenticated(self):
        c = _make_client()
        response = c.get("/api/me")
        assert response.status_code == 401

    def test_me_authenticated(self):
        c = _make_client()
        c.post(
            "/api/auth/login",
            json={"email": "testadmin@test.com", "password": "testpass123"},
        )
        response = c.get("/api/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testadmin@test.com"
        assert data["role"] == "admin"
        assert "*" in data["allowed_namespaces"]

    def test_logout(self):
        c = _make_client()
        c.post(
            "/api/auth/login",
            json={"email": "testadmin@test.com", "password": "testpass123"},
        )
        response = c.post("/api/auth/logout")
        assert response.status_code == 200


def _admin_client() -> TestClient:
    c = _make_client()
    c.post(
        "/api/auth/login",
        json={"email": "testadmin@test.com", "password": "testpass123"},
    )
    return c


class TestAdminEndpoints:
    def test_list_users(self):
        c = _admin_client()
        response = c.get("/api/admin/users")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    def test_create_user(self):
        c = _admin_client()
        response = c.post(
            "/api/admin/users",
            json={
                "email": "viewer@test.com",
                "password": "viewerpass",
                "role": "viewer",
                "allowed_namespaces": ["default", "kube-system"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "viewer@test.com"
        assert data["role"] == "viewer"
        assert data["allowed_namespaces"] == ["default", "kube-system"]

    def test_create_duplicate_user(self):
        c = _admin_client()
        response = c.post(
            "/api/admin/users",
            json={
                "email": "testadmin@test.com",
                "password": "pass",
                "role": "viewer",
                "allowed_namespaces": [],
            },
        )
        assert response.status_code == 409

    def test_update_user(self):
        c = _admin_client()
        users = c.get("/api/admin/users").json()
        viewer = next((u for u in users if u["email"] == "viewer@test.com"), None)
        if viewer:
            response = c.patch(
                f"/api/admin/users/{viewer['id']}",
                json={"allowed_namespaces": ["default"]},
            )
            assert response.status_code == 200
            assert response.json()["allowed_namespaces"] == ["default"]

    def test_unauthenticated_admin_access(self):
        c = _make_client()
        response = c.get("/api/admin/users")
        assert response.status_code == 401

    def test_theme_update(self):
        c = _admin_client()
        response = c.patch(
            "/api/me/theme",
            json={"theme_pref": "neo-brutal"},
        )
        assert response.status_code == 200
        assert response.json()["theme_pref"] == "neo-brutal"

    def test_invalid_theme(self):
        c = _admin_client()
        response = c.patch(
            "/api/me/theme",
            json={"theme_pref": "nonexistent"},
        )
        assert response.status_code == 400
