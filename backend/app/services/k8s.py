import os
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import List, Dict, Optional
from datetime import datetime, timezone

# Simple in-memory cache
# Key: (func_name, args...) -> (timestamp, data)
_CACHE = {}
CACHE_TTL = 15  # seconds

def cached(ttl=CACHE_TTL):
    def decorator(func):
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in _CACHE:
                timestamp, data = _CACHE[key]
                if now - timestamp < ttl:
                    return data

            # Call function
            result = func(*args, **kwargs)
            _CACHE[key] = (now, result)
            return result
        return wrapper
    return decorator

class K8sService:
    def __init__(self):
        self._load_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.batch_v1 = client.BatchV1Api()

    def _load_config(self):
        try:
            config.load_incluster_config()
            print("Loaded in-cluster config")
        except config.ConfigException:
            try:
                config.load_kube_config()
                print("Loaded kube config")
            except config.ConfigException:
                print("Warning: Could not load K8s config")

    def list_namespaces(self, allowed_namespaces: List[str], role: str) -> List[Dict]:
        try:
            # If admin, list all. If viewer, list only allowed.
            # However, simpler to just list all and filter, or just list allowed if we want to save calls.
            # But RBAC might prevent listing all.
            # If we have cluster-wide list permission (which we requested in RBAC), we list all and filter.

            ns_list = self.v1.list_namespace().items
            results = []
            for ns in ns_list:
                name = ns.metadata.name
                if role != "admin" and name not in allowed_namespaces and allowed_namespaces:
                    continue
                if role != "admin" and not allowed_namespaces:
                    # User has no namespaces
                    continue

                status = ns.status.phase
                results.append({
                    "name": name,
                    "status": status,
                    "age": ns.metadata.creation_timestamp
                })
            return results
        except ApiException as e:
            print(f"Error listing namespaces: {e}")
            return []

    def get_namespace_health(self, ns: str) -> str:
        # Check pods in namespace
        try:
            pods = self.v1.list_namespaced_pod(ns).items
            total = len(pods)
            if total == 0:
                return "Healthy"

            failed = 0
            pending = 0
            for pod in pods:
                phase = pod.status.phase
                if phase == "Failed":
                    failed += 1
                elif phase == "Pending":
                    pending += 1

                # Check container statuses for restarts/errors
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        if not cs.ready and cs.state.waiting:
                            if cs.state.waiting.reason in ["ImagePullBackOff", "CrashLoopBackOff", "ErrImagePull"]:
                                failed += 1 # Count as issue

            if failed > 0:
                return "Critical" if failed / total > 0.2 else "Degraded"
            if pending > 0:
                return "Degraded"
            return "Healthy"
        except ApiException:
            return "Unknown"

    def list_workloads(self, ns: str) -> Dict:
        try:
            deps = self.apps_v1.list_namespaced_deployment(ns).items
            sts = self.apps_v1.list_namespaced_stateful_set(ns).items
            ds = self.apps_v1.list_namespaced_daemon_set(ns).items

            return {
                "deployments": len(deps),
                "statefulsets": len(sts),
                "daemonsets": len(ds),
                "items": {
                    "deployments": [{"name": d.metadata.name, "ready": d.status.ready_replicas or 0, "desired": d.spec.replicas} for d in deps],
                    "statefulsets": [{"name": s.metadata.name, "ready": s.status.ready_replicas or 0, "desired": s.spec.replicas} for s in sts],
                    "daemonsets": [{"name": d.metadata.name, "ready": d.status.number_ready or 0, "desired": d.status.desired_number_scheduled} for d in ds]
                }
            }
        except ApiException as e:
            print(f"Error listing workloads for {ns}: {e}")
            return {"deployments": 0, "statefulsets": 0, "daemonsets": 0, "items": {}}

    def list_pods(self, ns: str) -> List[Dict]:
        try:
            pods = self.v1.list_namespaced_pod(ns).items
            results = []
            for pod in pods:
                restarts = 0
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        restarts += cs.restart_count

                results.append({
                    "name": pod.metadata.name,
                    "phase": pod.status.phase,
                    "restarts": restarts,
                    "node": pod.spec.node_name,
                    "startTime": pod.status.start_time,
                    "containers": [c.name for c in pod.spec.containers]
                })
            return results
        except ApiException as e:
            print(f"Error listing pods for {ns}: {e}")
            return []

    def get_pod_detail(self, ns: str, name: str) -> Dict:
        try:
            pod = self.v1.read_namespaced_pod(name, ns)
            events = self.v1.list_namespaced_event(ns, field_selector=f"involvedObject.name={name}").items

            event_list = []
            for e in events:
                event_list.append({
                    "type": e.type,
                    "reason": e.reason,
                    "message": e.message,
                    "count": e.count,
                    "lastTimestamp": e.last_timestamp
                })

            containers = []
            diagnosis = None

            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    state = "unknown"
                    reason = None
                    message = None

                    if cs.state.running:
                        state = "running"
                    elif cs.state.terminated:
                        state = "terminated"
                        reason = cs.state.terminated.reason
                        message = cs.state.terminated.message
                    elif cs.state.waiting:
                        state = "waiting"
                        reason = cs.state.waiting.reason
                        message = cs.state.waiting.message

                        # Diagnostics Rule Base
                        if reason == "ImagePullBackOff" or reason == "ErrImagePull":
                            diagnosis = f"Container {cs.name} cannot pull image. Check image name, tag, or pull secrets."
                        elif reason == "CrashLoopBackOff":
                            diagnosis = f"Container {cs.name} is crashing repeatedly. Check application logs for startup errors."
                        elif reason == "CreateContainerConfigError":
                            diagnosis = f"Container {cs.name} configuration error. Missing ConfigMap or Secret?"
                        elif reason == "OOMKilled": # Usually in terminated
                             diagnosis = f"Container {cs.name} ran out of memory. Increase memory limit."

                    if cs.state.terminated and cs.state.terminated.reason == "OOMKilled":
                        diagnosis = f"Container {cs.name} was OOMKilled (Out Of Memory). Increase memory limit."

                    containers.append({
                        "name": cs.name,
                        "state": state,
                        "ready": cs.ready,
                        "restartCount": cs.restart_count,
                        "reason": reason,
                        "message": message,
                        "image": cs.image
                    })

            return {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "node": pod.spec.node_name,
                "phase": pod.status.phase,
                "startTime": pod.status.start_time,
                "containers": containers,
                "events": event_list,
                "diagnosis": diagnosis
            }
        except ApiException as e:
            print(f"Error getting pod detail {name} in {ns}: {e}")
            return None

    def get_workload_detail(self, kind: str, ns: str, name: str) -> Dict:
        try:
            if kind == "deployments":
                obj = self.apps_v1.read_namespaced_deployment(name, ns)
            elif kind == "statefulsets":
                obj = self.apps_v1.read_namespaced_stateful_set(name, ns)
            elif kind == "daemonsets":
                obj = self.apps_v1.read_namespaced_daemon_set(name, ns)
            else:
                return None

            # Transform label selector to string
            selector_str = ""
            if obj.spec.selector and obj.spec.selector.match_labels:
                selector_str = ",".join([f"{k}={v}" for k, v in obj.spec.selector.match_labels.items()])

            pods = []
            if selector_str:
                pod_list = self.v1.list_namespaced_pod(ns, label_selector=selector_str).items
                for p in pod_list:
                    pods.append({
                        "name": p.metadata.name,
                        "phase": p.status.phase,
                        "restarts": sum(c.restart_count for c in p.status.container_statuses) if p.status.container_statuses else 0,
                    })

            return {
                "name": obj.metadata.name,
                "kind": kind,
                "namespace": obj.metadata.namespace,
                "replicas": obj.spec.replicas if hasattr(obj.spec, 'replicas') else None,
                "ready": obj.status.ready_replicas if hasattr(obj.status, 'ready_replicas') else (obj.status.number_ready if hasattr(obj.status, 'number_ready') else 0),
                "images": [c.image for c in obj.spec.template.spec.containers],
                "pods": pods,
                "conditions": [{"type": c.type, "status": c.status, "message": c.message} for c in obj.status.conditions] if hasattr(obj.status, 'conditions') and obj.status.conditions else []
            }
        except ApiException as e:
            print(f"Error getting workload detail {kind}/{name}: {e}")
            return None

    def list_events(self, ns: str) -> List[Dict]:
        try:
            events = self.v1.list_namespaced_event(ns).items
            # Sort by timestamp desc
            events.sort(key=lambda x: x.last_timestamp or x.event_time or x.metadata.creation_timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            results = []
            for e in events[:50]: # Top 50
                results.append({
                    "type": e.type,
                    "reason": e.reason,
                    "message": e.message,
                    "object": e.involved_object.kind + "/" + e.involved_object.name,
                    "count": e.count,
                    "time": e.last_timestamp or e.event_time
                })
            return results
        except ApiException:
            return []

k8s_service = K8sService()
