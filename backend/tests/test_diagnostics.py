"""Unit tests for the rule-based pod diagnostics engine."""

import pytest

from app.services.diagnostics import diagnose_pod


class TestDiagnosePodContainerStates:
    """Tests for container-state-based diagnosis."""

    def test_image_pull_backoff(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 0,
                "state": {"state": "waiting", "reason": "ImagePullBackOff", "message": ""},
                "last_state": None,
                "image": "nginx:nonexistent",
            }
        ]
        findings = diagnose_pod(containers, [])
        assert len(findings) == 1
        assert findings[0]["id"] == "image_pull_backoff"
        assert findings[0]["severity"] == "critical"
        assert "image" in findings[0]["title"].lower()

    def test_crash_loop_backoff(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 10,
                "state": {"state": "waiting", "reason": "CrashLoopBackOff", "message": ""},
                "last_state": {"state": "terminated", "reason": "Error", "exit_code": 1},
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        ids = {f["id"] for f in findings}
        assert "crash_loop" in ids

    def test_oom_killed(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 3,
                "state": {"state": "running"},
                "last_state": {"state": "terminated", "reason": "OOMKilled", "exit_code": 137},
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        ids = {f["id"] for f in findings}
        assert "oom_killed" in ids
        oom = next(f for f in findings if f["id"] == "oom_killed")
        assert oom["severity"] == "critical"
        assert "memory" in oom["description"].lower()

    def test_create_container_config_error(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 0,
                "state": {"state": "waiting", "reason": "CreateContainerConfigError", "message": "secret not found"},
                "last_state": None,
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        assert len(findings) == 1
        assert findings[0]["id"] == "config_error"
        assert "configmap" in findings[0]["remediation"].lower() or "secret" in findings[0]["remediation"].lower()

    def test_no_issues_healthy_pod(self):
        containers = [
            {
                "name": "app",
                "ready": True,
                "restart_count": 0,
                "state": {"state": "running"},
                "last_state": None,
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        assert len(findings) == 0


class TestDiagnosePodEvents:
    """Tests for event-based diagnosis."""

    def test_failed_scheduling(self):
        events = [
            {
                "type": "Warning",
                "reason": "FailedScheduling",
                "message": "0/3 nodes available: insufficient cpu",
                "count": 1,
            }
        ]
        findings = diagnose_pod([], events)
        ids = {f["id"] for f in findings}
        assert "failed_scheduling" in ids

    def test_failed_mount(self):
        events = [
            {
                "type": "Warning",
                "reason": "FailedMount",
                "message": "Unable to attach volume",
                "count": 1,
            }
        ]
        findings = diagnose_pod([], events)
        assert any(f["id"] == "failed_mount" for f in findings)

    def test_unhealthy_probe(self):
        events = [
            {
                "type": "Warning",
                "reason": "Unhealthy",
                "message": "Readiness probe failed: connection refused",
                "count": 5,
            }
        ]
        findings = diagnose_pod([], events)
        assert any(f["id"] == "liveness_failed" for f in findings)

    def test_backoff_event(self):
        events = [
            {
                "type": "Warning",
                "reason": "BackOff",
                "message": "Back-off restarting failed container",
                "count": 10,
            }
        ]
        findings = diagnose_pod([], events)
        assert any(f["id"] == "back_off_restart" for f in findings)


class TestDiagnosePodHighRestarts:
    """Tests for high restart count detection."""

    def test_high_restarts_detected(self):
        containers = [
            {
                "name": "app",
                "ready": True,
                "restart_count": 15,
                "state": {"state": "running"},
                "last_state": None,
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        assert any(f["id"] == "high_restarts" for f in findings)

    def test_low_restarts_not_flagged(self):
        containers = [
            {
                "name": "app",
                "ready": True,
                "restart_count": 2,
                "state": {"state": "running"},
                "last_state": None,
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        assert not any(f["id"] == "high_restarts" for f in findings)

    def test_crash_loop_suppresses_high_restarts(self):
        """When CrashLoopBackOff is detected, don't also flag high restarts."""
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 20,
                "state": {"state": "waiting", "reason": "CrashLoopBackOff"},
                "last_state": None,
                "image": "myapp:latest",
            }
        ]
        findings = diagnose_pod(containers, [])
        ids = {f["id"] for f in findings}
        assert "crash_loop" in ids
        # high_restarts should not appear since crash_loop covers it
        assert "high_restarts" not in ids


class TestDiagnosePodDeduplication:
    """Tests that the same rule isn't triggered multiple times."""

    def test_multiple_containers_same_issue(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 0,
                "state": {"state": "waiting", "reason": "ImagePullBackOff"},
                "last_state": None,
                "image": "img1:bad",
            },
            {
                "name": "sidecar",
                "ready": False,
                "restart_count": 0,
                "state": {"state": "waiting", "reason": "ImagePullBackOff"},
                "last_state": None,
                "image": "img2:bad",
            },
        ]
        findings = diagnose_pod(containers, [])
        image_pull_findings = [f for f in findings if f["id"] == "image_pull_backoff"]
        assert len(image_pull_findings) == 1  # Deduplicated

    def test_combined_container_and_event(self):
        containers = [
            {
                "name": "app",
                "ready": False,
                "restart_count": 0,
                "state": {"state": "waiting", "reason": "ImagePullBackOff"},
                "last_state": None,
                "image": "myapp:bad",
            }
        ]
        events = [
            {
                "type": "Warning",
                "reason": "FailedScheduling",
                "message": "insufficient cpu",
                "count": 1,
            }
        ]
        findings = diagnose_pod(containers, events)
        ids = {f["id"] for f in findings}
        assert "image_pull_backoff" in ids
        assert "failed_scheduling" in ids
        assert len(findings) == 2
