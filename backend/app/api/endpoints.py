from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from backend.app.services.auth import get_current_active_user
from backend.app.models.user import User
from backend.app.services.k8s import k8s_service

router = APIRouter()

def check_access(user: User, ns: str):
    if user.role == "admin":
        return
    if not user.allowed_namespaces:
         raise HTTPException(status_code=403, detail="No namespaces allowed")
    if ns not in user.allowed_namespaces:
        raise HTTPException(status_code=403, detail=f"Access to namespace '{ns}' denied")

@router.get("/namespaces")
def list_namespaces(
    user: User = Depends(get_current_active_user)
):
    namespaces = k8s_service.list_namespaces(user.allowed_namespaces, user.role)
    # Enhance with health status (parallelize in real app, sequential here for MVP simplicity)
    for ns in namespaces:
        ns['health'] = k8s_service.get_namespace_health(ns['name'])
    return namespaces

@router.get("/namespaces/{ns}/summary")
def get_namespace_summary(
    ns: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)

    health = k8s_service.get_namespace_health(ns)
    workloads = k8s_service.list_workloads(ns)
    pods = k8s_service.list_pods(ns)

    pod_count = len(pods)
    running = sum(1 for p in pods if p['phase'] == 'Running')
    failed = sum(1 for p in pods if p['phase'] == 'Failed')
    pending = sum(1 for p in pods if p['phase'] == 'Pending')
    restarts = sum(p.get('restarts', 0) for p in pods)

    return {
        "name": ns,
        "health": health,
        "counts": {
            "deployments": workloads['deployments'],
            "statefulsets": workloads['statefulsets'],
            "daemonsets": workloads['daemonsets'],
            "pods_total": pod_count,
            "pods_running": running,
            "pods_failed": failed,
            "pods_pending": pending,
            "restarts": restarts
        }
    }

@router.get("/namespaces/{ns}/workloads")
def get_namespace_workloads(
    ns: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)
    return k8s_service.list_workloads(ns)

@router.get("/namespaces/{ns}/pods")
def get_namespace_pods(
    ns: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)
    return k8s_service.list_pods(ns)

@router.get("/namespaces/{ns}/events")
def get_namespace_events(
    ns: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)
    return k8s_service.list_events(ns)

@router.get("/pods/{ns}/{name}")
def get_pod_detail(
    ns: str,
    name: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)
    detail = k8s_service.get_pod_detail(ns, name)
    if not detail:
        raise HTTPException(status_code=404, detail="Pod not found")
    return detail

@router.get("/workloads/{kind}/{ns}/{name}")
def get_workload_detail(
    kind: str,
    ns: str,
    name: str,
    user: User = Depends(get_current_active_user)
):
    check_access(user, ns)
    if kind not in ["deployments", "statefulsets", "daemonsets"]:
        raise HTTPException(status_code=400, detail="Invalid workload kind")

    detail = k8s_service.get_workload_detail(kind, ns, name)
    if not detail:
        raise HTTPException(status_code=404, detail="Workload not found")
    return detail
