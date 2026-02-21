import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_api_flow():
    # 1. Login as Admin
    login_data = {"username": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD}
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    # 2. Admin creates a Viewer user
    new_user = {
        "email": "viewer@example.com",
        "password": "password123",
        "role": "viewer",
        "allowed_namespaces": ["ns-allowed"]
    }
    response = client.post("/api/admin/users", json=new_user, headers=admin_headers)
    assert response.status_code == 200, f"Create user failed: {response.text}"
    created_user = response.json()
    assert created_user["email"] == "viewer@example.com"

    # 3. Login as Viewer
    login_data = {"username": "viewer@example.com", "password": "password123"}
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200, f"Viewer login failed: {response.text}"
    viewer_token = response.json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 4. Verify RBAC on /api/namespaces
    # Mock K8s service to return filtered list
    with patch("backend.app.services.k8s.k8s_service.list_namespaces") as mock_list_ns:
        with patch("backend.app.services.k8s.k8s_service.get_namespace_health") as mock_health:
            mock_list_ns.return_value = [{"name": "ns-allowed", "status": "Active"}]
            mock_health.return_value = "Healthy"

            response = client.get("/api/namespaces", headers=viewer_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "ns-allowed"

            # Verify k8s_service.list_namespaces was called with correct args
            mock_list_ns.assert_called_with(["ns-allowed"], "viewer")

    # 5. Verify Access Denied for forbidden namespace
    # Using check_access logic in endpoints.py
    # /api/namespaces/{ns}/summary calls check_access
    with patch("backend.app.services.k8s.k8s_service.get_namespace_health") as mock_health:
         with patch("backend.app.services.k8s.k8s_service.list_workloads") as mock_workloads:
             with patch("backend.app.services.k8s.k8s_service.list_pods") as mock_pods:
                response = client.get("/api/namespaces/forbidden-ns/summary", headers=viewer_headers)
                assert response.status_code == 403
