"""
Health & Status Tools.

Tools for checking pod health, events, and logs.
"""

from datetime import datetime, timedelta, timezone

from observer_mcp.clients.kubernetes import K8sClient
from observer_mcp.config import Settings, get_settings
from observer_mcp.models.kubernetes import (
    ContainerInfo,
    ContainerState,
    EventInfo,
    EventSeverity,
    PodInfo,
    PodPhase,
    PodStatus,
)
from observer_mcp.models.responses import (
    ToolResponse,
    ToolStatus,
    add_execution_metadata,
)
from observer_mcp.tools.base import parse_duration, tool_handler, truncate_logs


@tool_handler
def get_pod_status(
    namespace: str,
    selector: str | None = None,
    deployment_name: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get pod status for a namespace, deployment, or label selector.

    Provides detailed pod health information including phase, container states,
    restart counts, and node placement. Use this for quick health checks and
    understanding pod distribution.

    Args:
        namespace: Kubernetes namespace to query (required).
        selector: Label selector to filter pods (e.g., "app=backend").
        deployment_name: Alternative to selector - get pods for a specific deployment.
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - status: PodStatus object with counts and pod list
        - summary: Human-readable health summary

    Example:
        ```python
        # Get pods for a deployment
        result = get_pod_status(
            namespace="load-tester",
            deployment_name="local-backend"
        )

        # Get pods by label selector
        result = get_pod_status(
            namespace="load-tester",
            selector="tier=api"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    # Get pods
    if deployment_name:
        pods = k8s.get_pods_for_deployment(namespace, deployment_name)
    else:
        pods = k8s.list_pods(namespace=namespace, label_selector=selector)

    # Convert to PodInfo models
    pod_infos = []
    total_restarts = 0

    for pod in pods:
        containers = []
        pod_restarts = 0

        for status in pod.status.container_statuses or []:
            # Determine container state
            if status.state.running:
                state = ContainerState.RUNNING
            elif status.state.waiting:
                state = ContainerState.WAITING
            else:
                state = ContainerState.TERMINATED

            # Get last restart reason
            restart_reason = None
            if status.last_state and status.last_state.terminated:
                restart_reason = status.last_state.terminated.reason

            # Get resource specs from pod spec
            spec_container = next(
                (c for c in pod.spec.containers if c.name == status.name), None
            )
            resources = {}
            if spec_container and spec_container.resources:
                if spec_container.resources.requests:
                    resources["requests"] = dict(spec_container.resources.requests)
                if spec_container.resources.limits:
                    resources["limits"] = dict(spec_container.resources.limits)

            container = ContainerInfo(
                name=status.name,
                image=status.image,
                state=state,
                ready=status.ready,
                restart_count=status.restart_count,
                last_restart_reason=restart_reason,
                resources=resources,
            )
            containers.append(container)
            pod_restarts += status.restart_count

        total_restarts += pod_restarts

        # Map phase
        phase_map = {
            "Pending": PodPhase.PENDING,
            "Running": PodPhase.RUNNING,
            "Succeeded": PodPhase.SUCCEEDED,
            "Failed": PodPhase.FAILED,
        }
        phase = phase_map.get(pod.status.phase, PodPhase.UNKNOWN)

        pod_info = PodInfo(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace,
            phase=phase,
            node=pod.spec.node_name,
            ip=pod.status.pod_ip,
            created_at=pod.metadata.creation_timestamp,
            containers=containers,
            total_restart_count=pod_restarts,
            labels=pod.metadata.labels or {},
        )
        pod_infos.append(pod_info)

    # Calculate counts by phase
    running = sum(1 for p in pod_infos if p.phase == PodPhase.RUNNING)
    pending = sum(1 for p in pod_infos if p.phase == PodPhase.PENDING)
    failed = sum(1 for p in pod_infos if p.phase == PodPhase.FAILED)

    status = PodStatus(
        total_pods=len(pod_infos),
        running=running,
        pending=pending,
        failed=failed,
        total_restarts=total_restarts,
        pods=pod_infos,
    )

    # Generate summary
    if len(pod_infos) == 0:
        summary = "No pods found matching criteria"
    elif running == len(pod_infos) and total_restarts == 0:
        summary = f"All {running} pods healthy (Running, 0 restarts)"
    else:
        issues = []
        if pending > 0:
            issues.append(f"{pending} pending")
        if failed > 0:
            issues.append(f"{failed} failed")
        if total_restarts > 0:
            issues.append(f"{total_restarts} total restarts")
        summary = (
            f"{running}/{len(pod_infos)} pods running. Issues: {', '.join(issues)}"
        )

    return ToolResponse.success(
        result={
            "status": status.model_dump(),
            "summary": summary,
        },
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "selector": selector,
                "deployment_name": deployment_name,
            },
            start_time,
        ),
    )


@tool_handler
def get_recent_events(
    namespace: str | None = None,
    severity: str | None = None,
    time_window: str = "1h",
    involved_kind: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get recent Kubernetes events.

    Events are the first place to look when something breaks. This tool returns
    events like OOMKills, ImagePullErrors, FailedScheduling, etc., sorted by
    time (most recent first).

    Args:
        namespace: Namespace to query. If None, queries all namespaces.
        severity: Filter by event type: "Warning" or "Normal". If None, gets both.
        time_window: How far back to look. Options: "1h", "6h", "24h", "7d".
            Default is "1h".
        involved_kind: Filter by involved object kind (e.g., "Pod", "Deployment").
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - events: List of EventInfo objects, sorted by timestamp (newest first)
        - total_count: Total events found
        - warning_count: Number of Warning events
        - truncated: Whether the list was truncated to max_events limit

    Example:
        ```python
        # Get all warnings from last hour
        result = get_recent_events(
            namespace="load-tester",
            severity="Warning",
            time_window="1h"
        )

        # Get all events from last 24h
        result = get_recent_events(
            namespace="load-tester",
            time_window="24h"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    # Parse time window
    window_seconds = parse_duration(time_window)
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)

    # Build field selector
    field_selectors = []
    if severity:
        field_selectors.append(f"type={severity}")
    if involved_kind:
        field_selectors.append(f"involvedObject.kind={involved_kind}")

    field_selector = ",".join(field_selectors) if field_selectors else None

    # Get events
    events = k8s.list_events(
        namespace=namespace,
        field_selector=field_selector,
    )

    # Filter by time window
    filtered_events = []
    for event in events:
        event_time = event.last_timestamp or event.event_time
        if event_time and event_time >= cutoff_time:
            filtered_events.append(event)

    # Limit results
    max_events = settings.max_events
    truncated = len(filtered_events) > max_events
    filtered_events = filtered_events[:max_events]

    # Convert to EventInfo models
    event_infos = []
    warning_count = 0

    for event in filtered_events:
        event_type = (
            EventSeverity.WARNING if event.type == "Warning" else EventSeverity.NORMAL
        )
        if event_type == EventSeverity.WARNING:
            warning_count += 1

        info = EventInfo(
            name=event.metadata.name,
            namespace=event.metadata.namespace,
            type=event_type,
            reason=event.reason or "Unknown",
            message=event.message or "",
            involved_object={
                "kind": event.involved_object.kind if event.involved_object else "",
                "name": event.involved_object.name if event.involved_object else "",
            },
            first_seen=event.first_timestamp
            or event.event_time
            or datetime.now(timezone.utc),
            last_seen=event.last_timestamp
            or event.event_time
            or datetime.now(timezone.utc),
            count=event.count or 1,
            source=event.source.component if event.source else "unknown",
        )
        event_infos.append(info)

    warnings = []
    if truncated:
        warnings.append(
            f"Results truncated to {max_events} events. "
            f"Use narrower time_window or namespace filter."
        )

    result = ToolResponse(
        status=ToolStatus.PARTIAL if truncated else ToolStatus.SUCCESS,
        result={
            "events": [e.model_dump() for e in event_infos],
            "total_count": len(event_infos),
            "warning_count": warning_count,
            "truncated": truncated,
        },
        warnings=warnings,
        metadata=add_execution_metadata(
            {
                "namespace": namespace or "all",
                "severity": severity or "all",
                "time_window": time_window,
            },
            start_time,
        ),
    )
    return result


@tool_handler
def get_container_logs(
    namespace: str,
    pod_name: str,
    container_name: str | None = None,
    tail_lines: int = 100,
    since: str | None = None,
    previous: bool = False,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get logs from a container.

    Retrieves recent logs for debugging. Output is automatically truncated
    to prevent overwhelming the AI with too much data.

    Args:
        namespace: Pod namespace (required).
        pod_name: Pod name (required).
        container_name: Container name. Required for multi-container pods.
            If pod has single container, this can be omitted.
        tail_lines: Number of lines to retrieve from the end. Default 100,
            max 500 (enforced by settings).
        since: Get logs from this time window (e.g., "5m", "1h", "30m").
            If not set, gets last tail_lines lines.
        previous: If True, get logs from previous container instance
            (useful after a crash).
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - logs: Log content as string
        - line_count: Number of lines returned
        - truncated: Whether logs were truncated
        - pod_name: Pod that logs came from
        - container_name: Container that logs came from

    Example:
        ```python
        # Get last 100 lines from a pod
        result = get_container_logs(
            namespace="load-tester",
            pod_name="local-backend-abc123"
        )

        # Get logs from last 30 minutes
        result = get_container_logs(
            namespace="load-tester",
            pod_name="local-backend-abc123",
            since="30m"
        )

        # Get logs from crashed container
        result = get_container_logs(
            namespace="load-tester",
            pod_name="local-backend-abc123",
            previous=True
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    # Enforce max lines
    max_lines = min(tail_lines, settings.max_log_lines * 5)  # Allow up to 5x default
    tail_lines = min(tail_lines, max_lines)

    # Parse since to seconds
    since_seconds = None
    if since:
        since_seconds = parse_duration(since)

    # Get pod to find container name if not specified
    if not container_name:
        pod = k8s.get_pod(namespace, pod_name)
        if len(pod.spec.containers) > 1:
            containers = [c.name for c in pod.spec.containers]
            return ToolResponse.error(
                error_message=(
                    f"Pod has multiple containers: {containers}. "
                    f"Please specify container_name."
                ),
                error_type="MultipleContainersError",
            )
        container_name = pod.spec.containers[0].name

    # Get logs
    logs = k8s.get_pod_logs(
        namespace=namespace,
        name=pod_name,
        container=container_name,
        tail_lines=tail_lines,
        since_seconds=since_seconds,
        previous=previous,
    )

    # Check if truncation needed (shouldn't happen with tail_lines, but just in case)
    logs, truncated = truncate_logs(logs, max_lines)
    line_count = len(logs.split("\n")) if logs else 0

    warnings = []
    if truncated:
        warnings.append(
            f"Logs truncated to {max_lines} lines. "
            f"Use 'since' parameter to narrow the time range."
        )

    return ToolResponse(
        status=ToolStatus.PARTIAL if truncated else ToolStatus.SUCCESS,
        result={
            "logs": logs,
            "line_count": line_count,
            "truncated": truncated,
            "pod_name": pod_name,
            "container_name": container_name,
        },
        warnings=warnings,
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "pod_name": pod_name,
                "container_name": container_name,
                "tail_lines": tail_lines,
                "since": since,
                "previous": previous,
            },
            start_time,
        ),
    )
