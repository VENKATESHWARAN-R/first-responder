import pytest
from unittest.mock import MagicMock, patch
from backend.app.services.k8s import k8s_service

def test_list_namespaces_filtering():
    # Mock v1.list_namespace
    mock_ns_list = MagicMock()
    mock_ns1 = MagicMock()
    mock_ns1.metadata.name = "ns1"
    mock_ns1.status.phase = "Active"
    mock_ns1.metadata.creation_timestamp = None
    mock_ns2 = MagicMock()
    mock_ns2.metadata.name = "ns2"
    mock_ns2.status.phase = "Active"
    mock_ns2.metadata.creation_timestamp = None
    mock_ns_list.items = [mock_ns1, mock_ns2]

    with patch.object(k8s_service.v1, 'list_namespace', return_value=mock_ns_list):
        # Test admin
        result = k8s_service.list_namespaces([], "admin")
        assert len(result) == 2

        # Test viewer with access
        result = k8s_service.list_namespaces(["ns1"], "viewer")
        assert len(result) == 1
        assert result[0]["name"] == "ns1"

        # Test viewer no access
        result = k8s_service.list_namespaces([], "viewer")
        assert len(result) == 0

def test_diagnostics_logic():
    # Mock read_namespaced_pod
    mock_pod = MagicMock()
    mock_pod.metadata.name = "pod1"
    mock_pod.metadata.namespace = "ns1"
    mock_pod.spec.node_name = "node1"
    mock_pod.status.phase = "Pending"
    mock_pod.status.start_time = None

    container_status = MagicMock()
    container_status.name = "c1"
    container_status.state.running = None
    container_status.state.terminated = None
    container_status.state.waiting.reason = "ImagePullBackOff"
    container_status.state.waiting.message = "Err"
    container_status.ready = False
    container_status.restart_count = 0
    container_status.image = "img:tag"

    mock_pod.status.container_statuses = [container_status]

    with patch.object(k8s_service.v1, 'read_namespaced_pod', return_value=mock_pod):
        with patch.object(k8s_service.v1, 'list_namespaced_event', return_value=MagicMock(items=[])):
            detail = k8s_service.get_pod_detail("ns1", "pod1")
            assert detail is not None
            assert "cannot pull image" in detail["diagnosis"]
