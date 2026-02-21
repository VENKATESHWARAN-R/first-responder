"""Kubernetes read-only API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.services.auth import add_audit_log, filter_namespaces
from app.services.k8s import (
    get_namespace_summary,
    get_pod_detail,
    get_workload_detail,
    list_config,
    list_events,
    list_jobs,
    list_namespaces,
    list_pods,
    list_workloads,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["kubernetes"])


def _allowed_namespaces(user: dict) -> list[str]:
    """Get the list of namespaces this user may access."""
    try:
        all_ns = list_namespaces()
    except Exception as e:
        logger.error("Cannot list namespaces: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cluster API unreachable",
        )
    return filter_namespaces(user["allowed_namespaces"], all_ns)


def _check_ns_access(user: dict, ns: str) -> None:
    """Raise 403 if user cannot access the given namespace."""
    allowed = _allowed_namespaces(user)
    if ns not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to namespace '{ns}'",
        )


@router.get("/namespaces")
def get_namespaces(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Return summaries for all namespaces the user can access."""
    allowed = _allowed_namespaces(user)
    add_audit_log(user["id"], "view_namespaces", f"count={len(allowed)}")

    summaries = []
    for ns in allowed:
        try:
            summaries.append(get_namespace_summary(ns))
        except Exception as e:
            logger.warning("Error fetching summary for ns=%s: %s", ns, e)
            summaries.append({
                "name": ns,
                "health": "Unknown",
                "deployments_ready": 0,
                "deployments_total": 0,
                "pods_running": 0,
                "pods_pending": 0,
                "pods_failed": 0,
                "pods_total": 0,
                "top_restart_count": 0,
                "warning_events": 0,
                "last_refreshed": "",
            })
    return summaries


@router.get("/namespaces/{ns}/summary")
def get_ns_summary(ns: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _check_ns_access(user, ns)
    add_audit_log(user["id"], "view_namespace", f"ns={ns}")
    try:
        return get_namespace_summary(ns)
    except Exception as e:
        logger.error("Error fetching summary for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch namespace summary")


@router.get("/namespaces/{ns}/workloads")
def get_ns_workloads(ns: str, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    try:
        return list_workloads(ns)
    except Exception as e:
        logger.error("Error fetching workloads for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch workloads")


@router.get("/namespaces/{ns}/pods")
def get_ns_pods(ns: str, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    try:
        return list_pods(ns)
    except Exception as e:
        logger.error("Error fetching pods for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch pods")


@router.get("/namespaces/{ns}/events")
def get_ns_events(ns: str, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    try:
        return list_events(ns)
    except Exception as e:
        logger.error("Error fetching events for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch events")


@router.get("/namespaces/{ns}/config")
def get_ns_config(ns: str, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    try:
        return list_config(ns)
    except Exception as e:
        logger.error("Error fetching config for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch config")


@router.get("/namespaces/{ns}/jobs")
def get_ns_jobs(ns: str, user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    try:
        return list_jobs(ns)
    except Exception as e:
        logger.error("Error fetching jobs for ns=%s: %s", ns, e)
        raise HTTPException(status_code=503, detail="Failed to fetch jobs")


@router.get("/workloads/{kind}/{ns}/{name}")
def get_workload(
    kind: str,
    ns: str,
    name: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _check_ns_access(user, ns)
    valid_kinds = {"Deployment", "StatefulSet", "DaemonSet"}
    if kind not in valid_kinds:
        raise HTTPException(status_code=400, detail=f"Kind must be one of: {', '.join(valid_kinds)}")
    detail = get_workload_detail(kind, ns, name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"{kind} '{name}' not found in namespace '{ns}'")
    return detail


@router.get("/pods/{ns}/{name}")
def get_pod(
    ns: str,
    name: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _check_ns_access(user, ns)
    add_audit_log(user["id"], "view_pod", f"ns={ns} pod={name}")
    detail = get_pod_detail(ns, name)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Pod '{name}' not found in namespace '{ns}'")
    return detail
