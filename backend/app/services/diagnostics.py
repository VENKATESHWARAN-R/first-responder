"""Rule-based pod diagnostics — "Likely Cause" engine.

Analyses container statuses and pod events to generate
actionable diagnostic summaries. No LLM involved.
"""

from __future__ import annotations

from typing import Any

# ── Diagnostic Rules ──────────────────────────────────────────────────

RULES: list[dict[str, Any]] = [
    {
        "id": "image_pull_backoff",
        "match_reasons": ["ImagePullBackOff", "ErrImagePull"],
        "source": "container_state",
        "severity": "critical",
        "title": "Image Pull Failure",
        "description": (
            "The container image could not be pulled. This usually indicates "
            "a wrong image name/tag, missing registry credentials, or a "
            "private registry that the cluster cannot access."
        ),
        "remediation": (
            "1. Verify the image name and tag exist in the registry.\n"
            "2. Check if imagePullSecrets are configured correctly.\n"
            "3. Ensure the node can reach the container registry."
        ),
    },
    {
        "id": "crash_loop",
        "match_reasons": ["CrashLoopBackOff"],
        "source": "container_state",
        "severity": "critical",
        "title": "Application Crash Loop",
        "description": (
            "The container keeps crashing and restarting. The application "
            "is failing during startup or shortly after."
        ),
        "remediation": (
            "1. Check container logs for the crash reason.\n"
            "2. Verify environment variables and config are correct.\n"
            "3. Check if required services/dependencies are available.\n"
            "4. Look at the previous container state for exit codes."
        ),
    },
    {
        "id": "oom_killed",
        "match_reasons": ["OOMKilled"],
        "source": "container_state",
        "severity": "critical",
        "title": "Out of Memory (OOMKilled)",
        "description": (
            "The container was killed because it exceeded its memory limit. "
            "The kernel OOM killer terminated the process."
        ),
        "remediation": (
            "1. Increase the container's memory limit in the pod spec.\n"
            "2. Investigate the application for memory leaks.\n"
            "3. Profile memory usage to find the right limit."
        ),
    },
    {
        "id": "config_error",
        "match_reasons": ["CreateContainerConfigError"],
        "source": "container_state",
        "severity": "critical",
        "title": "Container Configuration Error",
        "description": (
            "The container could not be created due to a configuration "
            "problem — typically a missing ConfigMap, Secret, or "
            "environment variable reference."
        ),
        "remediation": (
            "1. Check that all referenced ConfigMaps and Secrets exist.\n"
            "2. Verify volume mount paths and names.\n"
            "3. Ensure env var references (valueFrom) point to existing keys."
        ),
    },
    {
        "id": "container_not_ready",
        "match_reasons": ["ContainersNotReady", "ContainerNotReady"],
        "source": "event",
        "severity": "warning",
        "title": "Container Readiness Failure",
        "description": (
            "One or more containers are not passing their readiness probes. "
            "The pod will not receive traffic until all containers are ready."
        ),
        "remediation": (
            "1. Check readiness probe configuration (path, port, thresholds).\n"
            "2. Verify the application is listening on the expected port.\n"
            "3. Check application logs for startup errors."
        ),
    },
    {
        "id": "back_off_restart",
        "match_reasons": ["BackOff"],
        "source": "event",
        "severity": "warning",
        "title": "Container Restart Back-Off",
        "description": (
            "Kubernetes is backing off from restarting the container. "
            "This typically follows repeated crashes."
        ),
        "remediation": (
            "1. Check container logs for the root cause of crashes.\n"
            "2. Look at terminated container state for exit codes.\n"
            "3. Verify application health and dependencies."
        ),
    },
    {
        "id": "failed_scheduling",
        "match_reasons": ["FailedScheduling"],
        "source": "event",
        "severity": "warning",
        "title": "Pod Scheduling Failure",
        "description": (
            "The scheduler could not place this pod on any node. "
            "Common reasons: insufficient resources, node selector "
            "mismatch, or taints/tolerations."
        ),
        "remediation": (
            "1. Check node resources (CPU/memory availability).\n"
            "2. Verify nodeSelector and affinity rules.\n"
            "3. Check for taints that lack matching tolerations."
        ),
    },
    {
        "id": "failed_mount",
        "match_reasons": ["FailedMount", "FailedAttachVolume"],
        "source": "event",
        "severity": "warning",
        "title": "Volume Mount Failure",
        "description": (
            "A volume could not be mounted to the pod. This can be "
            "caused by missing PVCs, storage class issues, or "
            "volume already attached to another node."
        ),
        "remediation": (
            "1. Check that the PersistentVolumeClaim exists and is bound.\n"
            "2. Verify storage class provisioner is working.\n"
            "3. For RWO volumes, ensure only one node tries to mount."
        ),
    },
    {
        "id": "liveness_failed",
        "match_reasons": ["Unhealthy"],
        "source": "event",
        "severity": "warning",
        "title": "Health Probe Failure",
        "description": (
            "The pod is failing liveness or readiness probes. "
            "If liveness fails repeatedly, the container will be restarted."
        ),
        "remediation": (
            "1. Check probe configuration (path, port, timeouts).\n"
            "2. Verify the application responds on the probe endpoint.\n"
            "3. Increase initialDelaySeconds if the app needs more startup time."
        ),
    },
]


def diagnose_pod(containers: list[dict], events: list[dict]) -> list[dict[str, str]]:
    """Run rule-based diagnostics on a pod's containers and events.

    Returns a list of diagnostic findings, each with:
      - id, severity, title, description, remediation, signal
    """
    findings: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    # Check container states
    for container in containers:
        state = container.get("state", {})
        last_state = container.get("last_state") or {}

        for src_state in [state, last_state]:
            reason = src_state.get("reason", "")
            if not reason:
                continue
            for rule in RULES:
                if rule["source"] != "container_state":
                    continue
                if reason in rule["match_reasons"] and rule["id"] not in seen_ids:
                    seen_ids.add(rule["id"])
                    findings.append({
                        "id": rule["id"],
                        "severity": rule["severity"],
                        "title": rule["title"],
                        "description": rule["description"],
                        "remediation": rule["remediation"],
                        "signal": f"Container '{container.get('name', '?')}' has reason: {reason}",
                    })

    # Check events
    for event in events:
        reason = event.get("reason", "")
        if not reason:
            continue
        for rule in RULES:
            if rule["source"] != "event":
                continue
            if reason in rule["match_reasons"] and rule["id"] not in seen_ids:
                seen_ids.add(rule["id"])
                findings.append({
                    "id": rule["id"],
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "description": rule["description"],
                    "remediation": rule["remediation"],
                    "signal": f"Event reason: {reason} — {event.get('message', '')}",
                })

    # Check high restart count
    for container in containers:
        if container.get("restart_count", 0) >= 5 and "crash_loop" not in seen_ids:
            seen_ids.add("high_restarts")
            findings.append({
                "id": "high_restarts",
                "severity": "warning",
                "title": "High Restart Count",
                "description": (
                    f"Container '{container.get('name', '?')}' has restarted "
                    f"{container.get('restart_count', 0)} times. This usually "
                    "indicates an unstable application that keeps crashing."
                ),
                "remediation": (
                    "1. Check container logs across restarts.\n"
                    "2. Look at the terminated state for exit codes.\n"
                    "3. Review resource limits and application stability."
                ),
                "signal": f"restart_count={container.get('restart_count', 0)}",
            })

    return findings
