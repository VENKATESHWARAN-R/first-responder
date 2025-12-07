"""
Analysis & Insights Tools.

Tools for analyzing patterns, history, and detecting anomalies.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

import numpy as np

from observer_mcp.clients.kubernetes import K8sClient
from observer_mcp.clients.prometheus import PrometheusClient
from observer_mcp.config import Settings, get_settings
from observer_mcp.models.kubernetes import (
    DeploymentHistoryEntry,
    RestartPattern,
)
from observer_mcp.models.metrics import (
    AnomalyInfo,
    MetricComparison,
)
from observer_mcp.models.responses import ToolResponse, add_execution_metadata
from observer_mcp.tools.base import parse_duration, tool_handler


@tool_handler
def analyze_restart_patterns(
    namespace: str,
    deployment_name: str | None = None,
    lookback_period: str = "24h",
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Analyze pod restart patterns to identify crash reasons and frequency.

    This is a semantic analysis tool that pre-processes restart data so the AI
    doesn't have to parse raw logs. Identifies patterns like periodic restarts,
    escalating crash loops, and categorizes crash reasons.

    Args:
        namespace: Kubernetes namespace to analyze (required).
        deployment_name: Specific deployment to analyze. If None, analyzes
            all pods in the namespace.
        lookback_period: How far back to analyze. Options: "1h", "6h", "24h", "7d", "30d".
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - pattern: RestartPattern object with analysis
        - severity: "none", "low", "medium", "high", "critical" based on restart rate
        - recommendation: Suggested action based on pattern

    Example:
        ```python
        # Analyze restarts for a specific deployment
        result = analyze_restart_patterns(
            namespace="load-tester",
            deployment_name="local-backend",
            lookback_period="24h"
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
        pods = k8s.list_pods(namespace=namespace)

    # Parse lookback period
    lookback_seconds = parse_duration(lookback_period)
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=lookback_seconds)

    # Collect restart information
    total_restarts = 0
    crash_reasons: Counter[str] = Counter()
    restart_times: list[datetime] = []
    affected_pods: list[str] = []

    for pod in pods:
        pod_restarts = 0

        if pod.status.container_statuses:
            for status in pod.status.container_statuses:
                pod_restarts += status.restart_count

                # Get crash reason from last terminated state
                if status.last_state and status.last_state.terminated:
                    reason = status.last_state.terminated.reason or "Unknown"
                    crash_reasons[reason] += status.restart_count

                    # Record restart time if within lookback
                    if status.last_state.terminated.finished_at:
                        finished = status.last_state.terminated.finished_at
                        if finished >= cutoff_time:
                            restart_times.append(finished)

        if pod_restarts > 0:
            affected_pods.append(pod.metadata.name)
            total_restarts += pod_restarts

    # Calculate restart rate
    hours = lookback_seconds / 3600
    restart_rate = total_restarts / hours if hours > 0 else 0

    # Detect pattern
    pattern_detected = None
    if len(restart_times) >= 3:
        # Sort restart times
        restart_times.sort()

        # Check for periodic pattern (similar intervals)
        if len(restart_times) >= 4:
            intervals = [
                (restart_times[i + 1] - restart_times[i]).total_seconds()
                for i in range(len(restart_times) - 1)
            ]
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)

            if std_interval < mean_interval * 0.3:  # Low variance = periodic
                pattern_detected = f"periodic (every ~{mean_interval / 60:.0f} minutes)"
            elif intervals[-1] < intervals[0] * 0.5:  # Increasing frequency
                pattern_detected = "escalating"
            else:
                pattern_detected = "random"

    # Determine severity
    if total_restarts == 0:
        severity = "none"
    elif restart_rate < 0.5:  # Less than 1 restart per 2 hours
        severity = "low"
    elif restart_rate < 2:  # Less than 2 restarts per hour
        severity = "medium"
    elif restart_rate < 6:  # Less than 6 restarts per hour
        severity = "high"
    else:
        severity = "critical"

    # Generate recommendation
    recommendations = []
    if "OOMKilled" in crash_reasons:
        recommendations.append("Increase memory limits - pods are being OOM killed")
    if "Error" in crash_reasons or "CrashLoopBackOff" in crash_reasons:
        recommendations.append("Check application logs for error details")
    if pattern_detected == "escalating":
        recommendations.append(
            "Urgent: Restart frequency is increasing - investigate immediately"
        )
    if pattern_detected and "periodic" in pattern_detected:
        recommendations.append(
            "Investigate for periodic memory leaks or external triggers"
        )
    if not recommendations and total_restarts > 0:
        recommendations.append("Review container logs and events for more context")

    pattern = RestartPattern(
        total_restarts=total_restarts,
        restart_rate_per_hour=round(restart_rate, 2),
        crash_reasons=dict(crash_reasons),
        restart_times=restart_times[-20:],  # Last 20 restart times
        pattern_detected=pattern_detected,
        affected_pods=affected_pods,
    )

    return ToolResponse.success(
        result={
            "pattern": pattern.model_dump(),
            "severity": severity,
            "recommendation": "; ".join(recommendations)
            if recommendations
            else "No issues detected",
        },
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "deployment_name": deployment_name,
                "lookback_period": lookback_period,
            },
            start_time,
        ),
    )


@tool_handler
def get_deployment_history(
    namespace: str,
    deployment_name: str,
    lookback_days: int = 7,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get deployment rollout history.

    Shows image version changes, scaling events, and configuration changes.
    Use this to correlate performance changes with deployments.

    Args:
        namespace: Deployment namespace (required).
        deployment_name: Deployment name (required).
        lookback_days: How many days of history to retrieve. Default 7.
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - history: List of DeploymentHistoryEntry objects
        - current_revision: Current active revision number
        - total_revisions: Total number of revisions found

    Example:
        ```python
        result = get_deployment_history(
            namespace="load-tester",
            deployment_name="local-backend",
            lookback_days=30
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    # Get deployment to find selector
    deployment = k8s.get_deployment(namespace, deployment_name)
    selector = deployment.spec.selector.match_labels
    label_selector = ",".join(f"{k}={v}" for k, v in selector.items())

    # Get ReplicaSets for this deployment
    replica_sets = k8s.list_replica_sets(namespace, label_selector)

    # Filter and sort by creation time
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    filtered_rs = [
        rs for rs in replica_sets if rs.metadata.creation_timestamp >= cutoff_time
    ]
    filtered_rs.sort(key=lambda rs: rs.metadata.creation_timestamp, reverse=True)

    # Extract history entries
    history = []
    current_revision = None

    for rs in filtered_rs:
        # Get revision number from annotation
        revision_str = (rs.metadata.annotations or {}).get(
            "deployment.kubernetes.io/revision", "0"
        )
        revision = int(revision_str)

        # Get image from pod template
        containers = rs.spec.template.spec.containers
        image = containers[0].image if containers else "unknown"

        # Get change cause annotation
        change_cause = (rs.metadata.annotations or {}).get("kubernetes.io/change-cause")

        # Check if this is the current revision
        if rs.status.replicas and rs.status.replicas > 0:
            if current_revision is None or revision > current_revision:
                current_revision = revision

        entry = DeploymentHistoryEntry(
            revision=revision,
            image=image,
            created_at=rs.metadata.creation_timestamp,
            replicas=rs.spec.replicas or 0,
            change_cause=change_cause,
        )
        history.append(entry)

    # Sort by revision descending
    history.sort(key=lambda h: h.revision, reverse=True)

    return ToolResponse.success(
        result={
            "history": [h.model_dump() for h in history],
            "current_revision": current_revision,
            "total_revisions": len(history),
        },
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "deployment_name": deployment_name,
                "lookback_days": lookback_days,
            },
            start_time,
        ),
    )


@tool_handler
def compare_period_metrics(
    namespace: str,
    deployment_name: str | None,
    metric: str,
    baseline_period: str,
    compare_period: str,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Compare metrics between two time periods.

    Useful for weekly/monthly reports and answering questions like
    "traffic up/down compared to last week/month".

    Args:
        namespace: Kubernetes namespace (required).
        deployment_name: Specific deployment to compare. If None, aggregates
            across all pods in the namespace.
        metric: Metric to compare. Options: "cpu", "memory", "network_rx", "network_tx".
        baseline_period: Baseline period description. Options:
            - "last_week" (7-14 days ago)
            - "last_month" (30-60 days ago)
            - Custom format: "7d ago to 14d ago"
        compare_period: Comparison period description. Options:
            - "this_week" (last 7 days)
            - "this_month" (last 30 days)
            - Custom format: "now to 7d ago"
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - comparison: MetricComparison object with statistics
        - summary: Human-readable comparison summary

    Example:
        ```python
        # Compare this week vs last week
        result = compare_period_metrics(
            namespace="load-tester",
            deployment_name="local-backend",
            metric="cpu",
            baseline_period="last_week",
            compare_period="this_week"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    prom = PrometheusClient(settings)

    # Build query
    if deployment_name:
        selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
    else:
        selector = f'namespace="{namespace}"'

    if metric == "cpu":
        query = f"sum(rate(container_cpu_usage_seconds_total{{{selector}}}[5m]))"
    elif metric == "memory":
        query = f"sum(container_memory_working_set_bytes{{{selector}}})"
    elif metric == "network_rx":
        query = f"sum(rate(container_network_receive_bytes_total{{{selector}}}[5m]))"
    elif metric == "network_tx":
        query = f"sum(rate(container_network_transmit_bytes_total{{{selector}}}[5m]))"
    else:
        return ToolResponse.error(
            error_message=f"Invalid metric: {metric}. Use 'cpu', 'memory', 'network_rx', or 'network_tx'.",
            error_type="ValidationError",
        )

    # Parse period definitions
    now = datetime.now(timezone.utc)

    def parse_period(period: str) -> tuple[datetime, datetime]:
        period = period.lower()
        if period == "this_week":
            return now - timedelta(days=7), now
        elif period == "last_week":
            return now - timedelta(days=14), now - timedelta(days=7)
        elif period == "this_month":
            return now - timedelta(days=30), now
        elif period == "last_month":
            return now - timedelta(days=60), now - timedelta(days=30)
        else:
            # Default to last 7 days
            return now - timedelta(days=7), now

    baseline_start, baseline_end = parse_period(baseline_period)
    compare_start, compare_end = parse_period(compare_period)

    # Query both periods
    baseline_results = prom.query_range(query, baseline_start, baseline_end)
    compare_results = prom.query_range(query, compare_start, compare_end)

    # Extract values
    def extract_values(results: list) -> list[float]:
        if not results or not results[0].get("values"):
            return []
        return [float(v[1]) for v in results[0]["values"] if v[1] != "NaN"]

    baseline_values = extract_values(baseline_results)
    compare_values = extract_values(compare_results)

    if not baseline_values or not compare_values:
        return ToolResponse.partial(
            result={"comparison": None, "summary": "Insufficient data for comparison."},
            warnings=["One or both periods have no data."],
            metadata=add_execution_metadata({}, start_time),
        )

    # Calculate statistics
    baseline_avg = float(np.mean(baseline_values))
    compare_avg = float(np.mean(compare_values))
    baseline_p95 = float(np.percentile(baseline_values, 95))
    compare_p95 = float(np.percentile(compare_values, 95))

    # Calculate percent change
    if baseline_avg == 0:
        percent_change = 0 if compare_avg == 0 else 100
    else:
        percent_change = ((compare_avg - baseline_avg) / baseline_avg) * 100

    # Determine significance (>10% change)
    is_significant = abs(percent_change) > 10

    # Generate notable differences
    notable = []
    if percent_change > 10:
        notable.append(f"{metric.upper()} increased by {percent_change:.1f}%")
    elif percent_change < -10:
        notable.append(f"{metric.upper()} decreased by {abs(percent_change):.1f}%")

    p95_change = (
        ((compare_p95 - baseline_p95) / baseline_p95 * 100) if baseline_p95 > 0 else 0
    )
    if abs(p95_change) > 20:
        direction = "increased" if p95_change > 0 else "decreased"
        notable.append(f"P95 {direction} by {abs(p95_change):.1f}%")

    comparison = MetricComparison(
        metric_name=metric,
        namespace=namespace,
        deployment_name=deployment_name,
        baseline_period=baseline_period,
        compare_period=compare_period,
        baseline_average=round(baseline_avg, 4),
        compare_average=round(compare_avg, 4),
        percent_change=round(percent_change, 1),
        is_significant=is_significant,
        baseline_p95=round(baseline_p95, 4),
        compare_p95=round(compare_p95, 4),
        notable_differences=notable,
    )

    # Generate summary
    direction = "up" if percent_change > 0 else "down"
    summary = f"{metric.upper()} is {direction} {abs(percent_change):.1f}% compared to {baseline_period}."
    if notable:
        summary += f" Notable: {'; '.join(notable)}"

    return ToolResponse.success(
        result={
            "comparison": comparison.model_dump(),
            "summary": summary,
        },
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "deployment_name": deployment_name,
                "metric": metric,
                "baseline_period": baseline_period,
                "compare_period": compare_period,
            },
            start_time,
        ),
    )


@tool_handler
def get_anomaly_report(
    namespace: str | None = None,
    lookback_period: str = "1h",
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get a report of detected anomalies across the cluster or namespace.

    Runs anomaly detection algorithms to identify issues like traffic spikes,
    unusual restart patterns, and resource exhaustion risks.

    Args:
        namespace: Namespace to analyze. If None, analyzes all namespaces.
        lookback_period: How far back to analyze. Options: "1h", "6h", "24h".
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - anomalies: List of AnomalyInfo objects
        - total_count: Total anomalies detected
        - critical_count: Number of critical anomalies
        - summary: Human-readable summary

    Example:
        ```python
        # Check for anomalies in a namespace
        result = get_anomaly_report(
            namespace="load-tester",
            lookback_period="1h"
        )

        # Check entire cluster
        result = get_anomaly_report(lookback_period="6h")
        ```

    Note:
        This uses simple threshold-based anomaly detection. For production use,
        consider implementing more sophisticated algorithms (ML-based, etc.).
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)
    prom = PrometheusClient(settings)

    anomalies: list[AnomalyInfo] = []
    lookback_seconds = parse_duration(lookback_period)

    # Determine namespaces to analyze
    if namespace:
        namespaces = [namespace]
    else:
        ns_list = k8s.list_namespaces()
        # Skip system namespaces
        namespaces = [
            ns.metadata.name
            for ns in ns_list
            if not ns.metadata.name.startswith("kube-")
            and ns.metadata.name not in ["default", "local-path-storage"]
        ]

    for ns in namespaces:
        # Check 1: High restart rate
        pods = k8s.list_pods(namespace=ns)
        for pod in pods:
            if pod.status.container_statuses:
                total_restarts = sum(
                    cs.restart_count for cs in pod.status.container_statuses
                )
                if total_restarts >= 5:  # 5+ restarts is concerning
                    severity = (
                        "critical"
                        if total_restarts >= 10
                        else "high"
                        if total_restarts >= 7
                        else "medium"
                    )

                    # Check for OOM
                    crash_reason = None
                    for cs in pod.status.container_statuses:
                        if cs.last_state and cs.last_state.terminated:
                            crash_reason = cs.last_state.terminated.reason

                    anomalies.append(
                        AnomalyInfo(
                            anomaly_type="restart_pattern",
                            severity=severity,
                            namespace=ns,
                            resource_name=pod.metadata.name,
                            resource_kind="Pod",
                            detected_at=datetime.now(timezone.utc),
                            description=f"Pod has {total_restarts} restarts"
                            + (
                                f" (last reason: {crash_reason})"
                                if crash_reason
                                else ""
                            ),
                            recommendation="Check container logs and events for crash reasons",
                        )
                    )

        # Check 2: Pods not running
        for pod in pods:
            if pod.status.phase in ("Pending", "Failed"):
                anomalies.append(
                    AnomalyInfo(
                        anomaly_type="pod_health",
                        severity="high" if pod.status.phase == "Failed" else "medium",
                        namespace=ns,
                        resource_name=pod.metadata.name,
                        resource_kind="Pod",
                        detected_at=datetime.now(timezone.utc),
                        description=f"Pod is in {pod.status.phase} state",
                        recommendation="Check pod events and node resources",
                    )
                )

        # Check 3: High memory usage (>80% of limit)
        try:
            memory_results = prom.query(
                f'100 * sum(container_memory_working_set_bytes{{namespace="{ns}"}}) by (pod) '
                f'/ sum(container_spec_memory_limit_bytes{{namespace="{ns}"}}) by (pod)'
            )

            for r in memory_results:
                pod_name = r.get("metric", {}).get("pod", "unknown")
                usage_percent = float(r.get("value", [0, "0"])[1])

                if usage_percent > 90:
                    anomalies.append(
                        AnomalyInfo(
                            anomaly_type="resource_exhaustion",
                            severity="critical",
                            namespace=ns,
                            resource_name=pod_name,
                            resource_kind="Pod",
                            detected_at=datetime.now(timezone.utc),
                            description=f"Memory usage at {usage_percent:.0f}% of limit",
                            metric_name="memory_usage_percent",
                            current_value=usage_percent,
                            expected_range=(0, 80),
                            recommendation="Increase memory limit or optimize memory usage",
                        )
                    )
                elif usage_percent > 80:
                    anomalies.append(
                        AnomalyInfo(
                            anomaly_type="resource_exhaustion",
                            severity="high",
                            namespace=ns,
                            resource_name=pod_name,
                            resource_kind="Pod",
                            detected_at=datetime.now(timezone.utc),
                            description=f"Memory usage at {usage_percent:.0f}% of limit",
                            metric_name="memory_usage_percent",
                            current_value=usage_percent,
                            expected_range=(0, 80),
                            recommendation="Monitor memory usage closely, may need to increase limits",
                        )
                    )
        except Exception:
            # Prometheus might not have data for this namespace
            pass

    # Count severities
    critical_count = sum(1 for a in anomalies if a.severity == "critical")
    high_count = sum(1 for a in anomalies if a.severity == "high")

    # Generate summary
    if not anomalies:
        summary = "No anomalies detected in the specified period."
    else:
        summary = f"Detected {len(anomalies)} anomalie(s): {critical_count} critical, {high_count} high."

    return ToolResponse.success(
        result={
            "anomalies": [a.model_dump() for a in anomalies],
            "total_count": len(anomalies),
            "critical_count": critical_count,
            "summary": summary,
        },
        metadata=add_execution_metadata(
            {"namespace": namespace or "all", "lookback_period": lookback_period},
            start_time,
        ),
    )
