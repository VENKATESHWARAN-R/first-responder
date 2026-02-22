from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from kubernetes import client, config
from kubernetes.client import ApiException
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings


class KubernetesService:
    def __init__(self) -> None:
        self._configured = False

    def _ensure_config(self) -> None:
        if self._configured:
            return
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()
        self.batch = client.BatchV1Api()
        self._configured = True

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(2), reraise=True)
    def _call(self, fn: Any) -> Any:
        return fn(_request_timeout=settings.k8s_timeout_seconds)

    def list_namespaces(self) -> list[str]:
        self._ensure_config()
        resp = self._call(lambda **kw: self.core.list_namespace(**kw))
        return [item.metadata.name for item in resp.items if item.metadata and item.metadata.name]

    def namespace_summary(self, namespace: str) -> dict[str, Any]:
        workloads = self.list_workloads(namespace)
        pods = self.list_pods(namespace)
        events = self.list_events(namespace)
        pod_states = Counter(p['phase'] for p in pods)
        top_restart = max((p['restart_count'] for p in pods), default=0)
        healthy = sum(1 for w in workloads if w['ready'] >= w['desired'] and w['desired'] > 0)
        warnings = sum(1 for event in events if event['type'] == 'Warning')
        health = 'Healthy'
        if warnings > 0 or healthy < len(workloads):
            health = 'Degraded'
        if warnings >= 5 or any(p['phase'] == 'Failed' for p in pods):
            health = 'Critical'
        return {
            'namespace': namespace,
            'health': health,
            'deployments': f'{healthy}/{len(workloads)}',
            'pods': {'running': pod_states.get('Running', 0), 'pending': pod_states.get('Pending', 0), 'failed': pod_states.get('Failed', 0)},
            'top_restart_count': top_restart,
            'last_refreshed': datetime.now(timezone.utc),
        }

    def list_workloads(self, namespace: str) -> list[dict[str, Any]]:
        self._ensure_config()
        result: list[dict[str, Any]] = []
        collectors = [
            ('Deployment', lambda: self.apps.list_namespaced_deployment(namespace)),
            ('StatefulSet', lambda: self.apps.list_namespaced_stateful_set(namespace)),
            ('DaemonSet', lambda: self.apps.list_namespaced_daemon_set(namespace)),
        ]
        for kind, fetch in collectors:
            resp = self._call(lambda **kw: fetch().to_dict() if False else fetch())
            for item in resp.items:
                spec_replicas = getattr(item.spec, 'replicas', 0) or 0
                ready = getattr(item.status, 'ready_replicas', 0) or 0
                if kind == 'DaemonSet':
                    spec_replicas = getattr(item.status, 'desired_number_scheduled', 0) or 0
                    ready = getattr(item.status, 'number_ready', 0) or 0
                images = []
                if item.spec and item.spec.template and item.spec.template.spec:
                    images = [c.image for c in (item.spec.template.spec.containers or []) if c.image]
                selector = {}
                if item.spec and getattr(item.spec, 'selector', None) and getattr(item.spec.selector, 'match_labels', None):
                    selector = item.spec.selector.match_labels or {}
                result.append({'kind': kind, 'name': item.metadata.name, 'namespace': namespace, 'desired': spec_replicas, 'ready': ready, 'images': images, 'selector': selector, 'conditions': [c.to_dict() for c in (item.status.conditions or [])]})
        return result

    def list_pods(self, namespace: str) -> list[dict[str, Any]]:
        self._ensure_config()
        resp = self._call(lambda **kw: self.core.list_namespaced_pod(namespace, **kw))
        pods: list[dict[str, Any]] = []
        for p in resp.items:
            statuses = p.status.container_statuses or []
            restarts = sum((s.restart_count or 0) for s in statuses)
            owners = [o.name for o in (p.metadata.owner_references or []) if o.name]
            pods.append({'name': p.metadata.name, 'phase': p.status.phase, 'node': p.spec.node_name, 'start_time': p.status.start_time, 'restart_count': restarts, 'owners': owners})
        return pods

    def get_pod(self, namespace: str, name: str) -> dict[str, Any]:
        self._ensure_config()
        pod = self._call(lambda **kw: self.core.read_namespaced_pod(name, namespace, **kw))
        statuses = []
        for s in pod.status.container_statuses or []:
            state_reason = ''
            message = ''
            if s.state.waiting:
                state_reason = s.state.waiting.reason or ''
                message = s.state.waiting.message or ''
                state = 'waiting'
            elif s.state.terminated:
                state_reason = s.state.terminated.reason or ''
                message = s.state.terminated.message or ''
                state = 'terminated'
            else:
                state = 'running'
            last_reason = s.last_state.terminated.reason if s.last_state and s.last_state.terminated else ''
            statuses.append({'name': s.name, 'state': state, 'state_reason': state_reason, 'last_state_reason': last_reason or '', 'restart_count': s.restart_count or 0, 'message': message})
        return {'name': name, 'namespace': namespace, 'phase': pod.status.phase, 'node': pod.spec.node_name, 'start_time': pod.status.start_time, 'container_statuses': statuses}

    def list_pods_by_selector(self, namespace: str, selector: dict[str, str]) -> list[dict[str, Any]]:
        if not selector:
            return []
        self._ensure_config()
        label_selector = ','.join(f'{key}={value}' for key, value in selector.items())
        resp = self._call(lambda **kw: self.core.list_namespaced_pod(namespace, label_selector=label_selector, **kw))
        pods: list[dict[str, Any]] = []
        for p in resp.items:
            statuses = p.status.container_statuses or []
            restarts = sum((s.restart_count or 0) for s in statuses)
            owners = [o.name for o in (p.metadata.owner_references or []) if o.name]
            pods.append({'name': p.metadata.name, 'phase': p.status.phase, 'node': p.spec.node_name, 'start_time': p.status.start_time, 'restart_count': restarts, 'owners': owners})
        return pods

    def list_events(self, namespace: str) -> list[dict[str, Any]]:
        self._ensure_config()
        try:
            resp = self._call(lambda **kw: self.core.list_namespaced_event(namespace, **kw))
        except ApiException:
            return []
        events = []
        for e in resp.items:
            events.append({'type': e.type or 'Normal', 'reason': e.reason or '', 'message': e.message or '', 'obj': e.involved_object.name if e.involved_object else '', 'time': e.last_timestamp or e.event_time or e.metadata.creation_timestamp})
        events.sort(key=lambda item: item['time'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return events

    def list_config(self, namespace: str) -> dict[str, list[str]]:
        self._ensure_config()
        cms = self._call(lambda **kw: self.core.list_namespaced_config_map(namespace, **kw))
        secrets = self._call(lambda **kw: self.core.list_namespaced_secret(namespace, **kw))
        return {'configmaps': [c.metadata.name for c in cms.items], 'secrets': [s.metadata.name for s in secrets.items]}


k8s_service = KubernetesService()
