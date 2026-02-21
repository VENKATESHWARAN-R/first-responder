"""Kubernetes API client service — read-only operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.config import settings
from app.services.cache import cache
from app.services.diagnostics import diagnose_pod

logger = logging.getLogger(__name__)

_api_core: client.CoreV1Api | None = None
_api_apps: client.AppsV1Api | None = None
_api_batch: client.BatchV1Api | None = None


def init_k8s() -> None:
    """Initialize the Kubernetes client."""
    global _api_core, _api_apps, _api_batch
    try:
        if settings.k8s_in_cluster:
            config.load_incluster_config()
        else:
            config.load_kube_config(config_file=settings.k8s_kubeconfig)
        _api_core = client.CoreV1Api()
        _api_apps = client.AppsV1Api()
        _api_batch = client.BatchV1Api()
        logger.info("Kubernetes client initialized (in_cluster=%s)", settings.k8s_in_cluster)
    except Exception:
        logger.warning("Could not initialize Kubernetes client. K8s features will be unavailable.")
        _api_core = None
        _api_apps = None
        _api_batch = None


def _core() -> client.CoreV1Api:
    if _api_core is None:
        raise RuntimeError("Kubernetes client not initialized")
    return _api_core


def _apps() -> client.AppsV1Api:
    if _api_apps is None:
        raise RuntimeError("Kubernetes client not initialized")
    return _api_apps


def _batch() -> client.BatchV1Api:
    if _api_batch is None:
        raise RuntimeError("Kubernetes client not initialized")
    return _api_batch


def _ts(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Namespaces ────────────────────────────────────────────────────────

def list_namespaces() -> list[str]:
    """Return all namespace names from the cluster."""
    key = "ns:list"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        ns_list = _core().list_namespace(timeout_seconds=10)
        names = [ns.metadata.name for ns in ns_list.items]
        cache.set(key, names)
        return names
    except ApiException as e:
        logger.error("Failed to list namespaces: %s", e.reason)
        raise


# ── Namespace Summary ─────────────────────────────────────────────────

def get_namespace_summary(ns: str) -> dict[str, Any]:
    """Build a health summary for a single namespace."""
    key = f"ns:summary:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    deployments = _list_deployments(ns)
    pods = _list_pods(ns)
    events = _list_events(ns)

    deps_ready = sum(1 for d in deployments if _deployment_is_ready(d))
    deps_total = len(deployments)

    pods_running = sum(1 for p in pods if p.get("phase") == "Running")
    pods_pending = sum(1 for p in pods if p.get("phase") == "Pending")
    pods_failed = sum(1 for p in pods if p.get("phase") == "Failed")
    pods_total = len(pods)

    restart_counts = [p.get("restart_count", 0) for p in pods]
    top_restart = max(restart_counts) if restart_counts else 0

    warning_events = sum(1 for e in events if e.get("type") == "Warning")

    health = _compute_health(deps_ready, deps_total, pods_failed, warning_events)

    summary = {
        "name": ns,
        "health": health,
        "deployments_ready": deps_ready,
        "deployments_total": deps_total,
        "pods_running": pods_running,
        "pods_pending": pods_pending,
        "pods_failed": pods_failed,
        "pods_total": pods_total,
        "top_restart_count": top_restart,
        "warning_events": warning_events,
        "last_refreshed": _now_iso(),
    }
    cache.set(key, summary)
    return summary


def _compute_health(deps_ready: int, deps_total: int, pods_failed: int, warning_events: int) -> str:
    if pods_failed > 0 or (deps_total > 0 and deps_ready == 0):
        return "Critical"
    if (deps_total > 0 and deps_ready < deps_total) or warning_events > 5:
        return "Degraded"
    return "Healthy"


def _deployment_is_ready(d: dict) -> bool:
    return d.get("ready", 0) >= d.get("desired", 1) and d.get("desired", 0) > 0


# ── Workloads ─────────────────────────────────────────────────────────

def list_workloads(ns: str) -> list[dict[str, Any]]:
    """List Deployments, StatefulSets, DaemonSets in a namespace."""
    key = f"ns:workloads:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = _list_deployments(ns) + _list_statefulsets(ns) + _list_daemonsets(ns)
    cache.set(key, result)
    return result


def _list_deployments(ns: str) -> list[dict[str, Any]]:
    try:
        deps = _apps().list_namespaced_deployment(ns, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for d in deps.items:
        spec = d.spec
        status = d.status
        conditions = []
        if status.conditions:
            conditions = [
                {"type": c.type, "status": c.status, "message": c.message or ""}
                for c in status.conditions
            ]
        images = []
        if spec.template and spec.template.spec and spec.template.spec.containers:
            images = [c.image for c in spec.template.spec.containers if c.image]
        result.append({
            "kind": "Deployment",
            "name": d.metadata.name,
            "namespace": ns,
            "desired": spec.replicas or 0,
            "ready": status.ready_replicas or 0,
            "available": status.available_replicas or 0,
            "images": images,
            "conditions": conditions,
        })
    return result


def _list_statefulsets(ns: str) -> list[dict[str, Any]]:
    try:
        sts = _apps().list_namespaced_stateful_set(ns, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for s in sts.items:
        images = []
        if s.spec.template and s.spec.template.spec and s.spec.template.spec.containers:
            images = [c.image for c in s.spec.template.spec.containers if c.image]
        conditions = []
        if s.status.conditions:
            conditions = [
                {"type": c.type, "status": c.status, "message": c.message or ""}
                for c in s.status.conditions
            ]
        result.append({
            "kind": "StatefulSet",
            "name": s.metadata.name,
            "namespace": ns,
            "desired": s.spec.replicas or 0,
            "ready": s.status.ready_replicas or 0,
            "available": s.status.ready_replicas or 0,
            "images": images,
            "conditions": conditions,
        })
    return result


def _list_daemonsets(ns: str) -> list[dict[str, Any]]:
    try:
        dss = _apps().list_namespaced_daemon_set(ns, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for ds in dss.items:
        images = []
        if ds.spec.template and ds.spec.template.spec and ds.spec.template.spec.containers:
            images = [c.image for c in ds.spec.template.spec.containers if c.image]
        result.append({
            "kind": "DaemonSet",
            "name": ds.metadata.name,
            "namespace": ns,
            "desired": ds.status.desired_number_scheduled or 0,
            "ready": ds.status.number_ready or 0,
            "available": ds.status.number_available or 0,
            "images": images,
            "conditions": [],
        })
    return result


def get_workload_detail(kind: str, ns: str, name: str) -> dict[str, Any] | None:
    """Get detail for a specific workload."""
    key = f"workload:{kind}:{ns}:{name}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    fetchers = {
        "Deployment": _get_deployment_detail,
        "StatefulSet": _get_statefulset_detail,
        "DaemonSet": _get_daemonset_detail,
    }
    fetcher = fetchers.get(kind)
    if fetcher is None:
        return None
    detail = fetcher(ns, name)
    if detail:
        # Get pods for this workload
        pods = _list_pods(ns)
        workload_pods = _match_pods_to_workload(kind, name, pods, ns)
        detail["pods"] = workload_pods
        cache.set(key, detail)
    return detail


def _get_deployment_detail(ns: str, name: str) -> dict[str, Any] | None:
    try:
        d = _apps().read_namespaced_deployment(name, ns)
    except ApiException:
        return None
    conditions = []
    if d.status.conditions:
        conditions = [
            {"type": c.type, "status": c.status, "message": c.message or "", "reason": c.reason or ""}
            for c in d.status.conditions
        ]
    images = []
    if d.spec.template and d.spec.template.spec and d.spec.template.spec.containers:
        images = [c.image for c in d.spec.template.spec.containers if c.image]
    return {
        "kind": "Deployment",
        "name": name,
        "namespace": ns,
        "desired": d.spec.replicas or 0,
        "ready": d.status.ready_replicas or 0,
        "available": d.status.available_replicas or 0,
        "images": images,
        "conditions": conditions,
        "selector": d.spec.selector.match_labels if d.spec.selector else {},
    }


def _get_statefulset_detail(ns: str, name: str) -> dict[str, Any] | None:
    try:
        s = _apps().read_namespaced_stateful_set(name, ns)
    except ApiException:
        return None
    conditions = []
    if s.status.conditions:
        conditions = [
            {"type": c.type, "status": c.status, "message": c.message or "", "reason": c.reason or ""}
            for c in s.status.conditions
        ]
    images = []
    if s.spec.template and s.spec.template.spec and s.spec.template.spec.containers:
        images = [c.image for c in s.spec.template.spec.containers if c.image]
    return {
        "kind": "StatefulSet",
        "name": name,
        "namespace": ns,
        "desired": s.spec.replicas or 0,
        "ready": s.status.ready_replicas or 0,
        "available": s.status.ready_replicas or 0,
        "images": images,
        "conditions": conditions,
        "selector": s.spec.selector.match_labels if s.spec.selector else {},
    }


def _get_daemonset_detail(ns: str, name: str) -> dict[str, Any] | None:
    try:
        ds = _apps().read_namespaced_daemon_set(name, ns)
    except ApiException:
        return None
    images = []
    if ds.spec.template and ds.spec.template.spec and ds.spec.template.spec.containers:
        images = [c.image for c in ds.spec.template.spec.containers if c.image]
    return {
        "kind": "DaemonSet",
        "name": name,
        "namespace": ns,
        "desired": ds.status.desired_number_scheduled or 0,
        "ready": ds.status.number_ready or 0,
        "available": ds.status.number_available or 0,
        "images": images,
        "conditions": [],
        "selector": ds.spec.selector.match_labels if ds.spec.selector else {},
    }


def _match_pods_to_workload(kind: str, name: str, pods: list[dict], ns: str) -> list[dict]:
    """Simple heuristic: match pods whose name starts with the workload name."""
    matched = []
    for p in pods:
        pod_name: str = p.get("name", "")
        if kind == "DaemonSet":
            if pod_name.startswith(f"{name}-"):
                matched.append(p)
        else:
            # Deployment pods: <deployment>-<replicaset-hash>-<pod-hash>
            # StatefulSet pods: <sts>-<ordinal>
            if pod_name.startswith(f"{name}-"):
                matched.append(p)
    return matched


# ── Pods ──────────────────────────────────────────────────────────────

def list_pods(ns: str) -> list[dict[str, Any]]:
    """List pods (uses cache)."""
    key = f"ns:pods:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = _list_pods(ns)
    cache.set(key, result)
    return result


def _list_pods(ns: str) -> list[dict[str, Any]]:
    try:
        pod_list = _core().list_namespaced_pod(ns, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for p in pod_list.items:
        containers = _extract_container_statuses(p.status)
        restart_count = sum(c.get("restart_count", 0) for c in containers)
        result.append({
            "name": p.metadata.name,
            "namespace": ns,
            "phase": p.status.phase or "Unknown",
            "node": p.spec.node_name,
            "start_time": _ts(p.status.start_time),
            "restart_count": restart_count,
            "containers": containers,
        })
    return result


def get_pod_detail(ns: str, name: str) -> dict[str, Any] | None:
    """Get full pod detail with events and diagnostics."""
    key = f"pod:{ns}:{name}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        p = _core().read_namespaced_pod(name, ns)
    except ApiException:
        return None

    containers = _extract_container_statuses(p.status)
    restart_count = sum(c.get("restart_count", 0) for c in containers)

    # Pod events
    events = _get_pod_events(ns, name)

    # Diagnostics
    likely_causes = diagnose_pod(containers, events)

    detail = {
        "name": name,
        "namespace": ns,
        "phase": p.status.phase or "Unknown",
        "node": p.spec.node_name,
        "start_time": _ts(p.status.start_time),
        "restart_count": restart_count,
        "containers": containers,
        "events": events,
        "likely_causes": likely_causes,
    }
    cache.set(key, detail)
    return detail


def _extract_container_statuses(status) -> list[dict[str, Any]]:
    containers: list[dict[str, Any]] = []
    all_statuses = list(status.container_statuses or []) + list(status.init_container_statuses or [])
    for cs in all_statuses:
        state = _extract_state(cs.state) if cs.state else {"state": "unknown"}
        last_state = _extract_state(cs.last_state) if cs.last_state else None

        containers.append({
            "name": cs.name,
            "ready": cs.ready,
            "restart_count": cs.restart_count or 0,
            "state": state,
            "last_state": last_state,
            "image": cs.image,
        })
    return containers


def _extract_state(state) -> dict[str, Any]:
    if state.running:
        return {"state": "running", "started_at": _ts(state.running.started_at)}
    if state.waiting:
        return {
            "state": "waiting",
            "reason": state.waiting.reason or "",
            "message": state.waiting.message or "",
        }
    if state.terminated:
        return {
            "state": "terminated",
            "reason": state.terminated.reason or "",
            "message": state.terminated.message or "",
            "exit_code": state.terminated.exit_code,
        }
    return {"state": "unknown"}


def _get_pod_events(ns: str, pod_name: str) -> list[dict[str, Any]]:
    try:
        field = f"involvedObject.name={pod_name}"
        events = _core().list_namespaced_event(ns, field_selector=field, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for e in events.items:
        result.append({
            "type": e.type or "Normal",
            "reason": e.reason or "",
            "message": e.message or "",
            "source": f"{e.source.component or ''}" if e.source else "",
            "first_seen": _ts(e.first_timestamp),
            "last_seen": _ts(e.last_timestamp),
            "count": e.count or 1,
            "involved_object": f"{e.involved_object.kind}/{e.involved_object.name}" if e.involved_object else "",
        })
    result.sort(key=lambda x: x.get("last_seen") or "", reverse=True)
    return result


# ── Events ────────────────────────────────────────────────────────────

def list_events(ns: str) -> list[dict[str, Any]]:
    key = f"ns:events:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        events = _core().list_namespaced_event(ns, timeout_seconds=10)
    except ApiException:
        return []
    result = []
    for e in events.items:
        result.append({
            "type": e.type or "Normal",
            "reason": e.reason or "",
            "message": e.message or "",
            "source": f"{e.source.component or ''}" if e.source else "",
            "first_seen": _ts(e.first_timestamp),
            "last_seen": _ts(e.last_timestamp),
            "count": e.count or 1,
            "involved_object": f"{e.involved_object.kind}/{e.involved_object.name}" if e.involved_object else "",
        })
    result.sort(key=lambda x: x.get("last_seen") or "", reverse=True)
    cache.set(key, result)
    return result


# ── Config ────────────────────────────────────────────────────────────

def list_config(ns: str) -> list[dict[str, Any]]:
    """List ConfigMap and Secret names (no contents)."""
    key = f"ns:config:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result: list[dict[str, Any]] = []
    try:
        cms = _core().list_namespaced_config_map(ns, timeout_seconds=10)
        for cm in cms.items:
            result.append({"kind": "ConfigMap", "name": cm.metadata.name, "namespace": ns})
    except ApiException:
        pass
    try:
        secrets = _core().list_namespaced_secret(ns, timeout_seconds=10)
        for s in secrets.items:
            result.append({"kind": "Secret", "name": s.metadata.name, "namespace": ns})
    except ApiException:
        pass
    cache.set(key, result)
    return result


# ── Jobs / CronJobs ──────────────────────────────────────────────────

def list_jobs(ns: str) -> list[dict[str, Any]]:
    key = f"ns:jobs:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result: list[dict[str, Any]] = []
    try:
        jobs = _batch().list_namespaced_job(ns, timeout_seconds=10)
        for j in jobs.items:
            result.append({
                "kind": "Job",
                "name": j.metadata.name,
                "namespace": ns,
                "active": j.status.active or 0,
                "succeeded": j.status.succeeded or 0,
                "failed": j.status.failed or 0,
                "start_time": _ts(j.status.start_time),
                "completion_time": _ts(j.status.completion_time),
            })
    except ApiException:
        pass
    try:
        crons = _batch().list_namespaced_cron_job(ns, timeout_seconds=10)
        for c in crons.items:
            result.append({
                "kind": "CronJob",
                "name": c.metadata.name,
                "namespace": ns,
                "schedule": c.spec.schedule,
                "last_schedule": _ts(c.status.last_schedule_time),
                "active": len(c.status.active) if c.status.active else 0,
            })
    except ApiException:
        pass
    cache.set(key, result)
    return result
