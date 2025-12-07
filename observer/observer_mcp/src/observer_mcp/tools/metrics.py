"""
Metrics & Monitoring Tools.

Tools for querying Prometheus metrics and analyzing resource usage.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from observer_mcp.clients.prometheus import PrometheusClient
from observer_mcp.config import Settings, get_settings
from observer_mcp.models.metrics import (
    ResourceTrend,
    ResourceUsage,
    TimeseriesDataPoint,
    TimeseriesResult,
    TrendDirection,
)
from observer_mcp.models.responses import (
    ToolResponse,
    ToolStatus,
    add_execution_metadata,
)
from observer_mcp.tools.base import parse_duration, tool_handler


@tool_handler
def get_current_resource_usage(
    namespace: str,
    deployment_name: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get current CPU and memory usage for pods.

    Provides real-time resource consumption compared to limits/requests.
    Use this for quick health checks and answering "is this pod healthy"
    or "are we hitting resource limits".

    Args:
        namespace: Kubernetes namespace to query (required).
        deployment_name: Specific deployment to filter. If None, gets all
            pods in the namespace.
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - usage: List of ResourceUsage objects per pod
        - summary: Aggregated summary with totals and alerts

    Example:
        ```python
        # Get usage for all pods in namespace
        result = get_current_resource_usage(namespace="load-tester")

        # Get usage for specific deployment
        result = get_current_resource_usage(
            namespace="load-tester",
            deployment_name="local-backend"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    prom = PrometheusClient(settings)

    # Get CPU and memory usage
    cpu_results = prom.get_container_cpu_usage(namespace, deployment_name)
    memory_results = prom.get_container_memory_usage(namespace, deployment_name)
    limits = prom.get_resource_limits(namespace, deployment_name)

    # Build lookup maps for limits
    def build_lookup(results: list[dict]) -> dict[str, float]:
        """Build pod->value lookup from Prometheus results."""
        lookup = {}
        for r in results:
            pod = r.get("metric", {}).get("pod", "")
            value = float(r.get("value", [0, "0"])[1])
            lookup[pod] = value
        return lookup

    cpu_limits_map = build_lookup(limits.get("cpu_limits", []))
    cpu_requests_map = build_lookup(limits.get("cpu_requests", []))
    memory_limits_map = build_lookup(limits.get("memory_limits", []))
    memory_requests_map = build_lookup(limits.get("memory_requests", []))

    # Process CPU results
    usage_list = []
    alerts = []

    # Merge CPU and memory by pod name
    pods_data: dict[str, dict[str, Any]] = {}

    for r in cpu_results:
        pod = r.get("metric", {}).get("pod", "unknown")
        value = float(r.get("value", [0, "0"])[1])
        if pod not in pods_data:
            pods_data[pod] = {}
        pods_data[pod]["cpu_usage"] = value

    for r in memory_results:
        pod = r.get("metric", {}).get("pod", "unknown")
        value = float(r.get("value", [0, "0"])[1])
        if pod not in pods_data:
            pods_data[pod] = {}
        pods_data[pod]["memory_usage"] = int(value)

    # Build ResourceUsage objects
    for pod, data in pods_data.items():
        cpu_usage = data.get("cpu_usage", 0.0)
        memory_usage = data.get("memory_usage", 0)

        cpu_limit = cpu_limits_map.get(pod)
        cpu_request = cpu_requests_map.get(pod)
        memory_limit = memory_limits_map.get(pod)
        memory_request = memory_requests_map.get(pod)

        # Calculate percentages
        cpu_percent = None
        if cpu_limit and cpu_limit > 0:
            cpu_percent = (cpu_usage / cpu_limit) * 100

        memory_percent = None
        if memory_limit and memory_limit > 0:
            memory_percent = (memory_usage / memory_limit) * 100

        usage = ResourceUsage(
            pod_name=pod,
            namespace=namespace,
            cpu_usage_cores=round(cpu_usage, 4),
            cpu_usage_percent=round(cpu_percent, 1) if cpu_percent else None,
            cpu_request_cores=round(cpu_request, 4) if cpu_request else None,
            cpu_limit_cores=round(cpu_limit, 4) if cpu_limit else None,
            memory_usage_bytes=memory_usage,
            memory_usage_mb=round(memory_usage / (1024 * 1024), 2),
            memory_usage_percent=round(memory_percent, 1) if memory_percent else None,
            memory_request_bytes=int(memory_request) if memory_request else None,
            memory_limit_bytes=int(memory_limit) if memory_limit else None,
        )
        usage_list.append(usage)

        # Check for alerts
        if usage.is_cpu_throttled:
            alerts.append(f"Pod {pod} CPU usage at {cpu_percent:.0f}% of limit")
        if usage.is_memory_pressure:
            alerts.append(f"Pod {pod} memory usage at {memory_percent:.0f}% of limit")

    # Generate summary
    total_cpu = sum(u.cpu_usage_cores for u in usage_list)
    total_memory_mb = sum(u.memory_usage_mb for u in usage_list)

    summary = {
        "pod_count": len(usage_list),
        "total_cpu_cores": round(total_cpu, 4),
        "total_memory_mb": round(total_memory_mb, 2),
        "alerts": alerts,
    }

    return ToolResponse.success(
        result={
            "usage": [u.model_dump() for u in usage_list],
            "summary": summary,
        },
        metadata=add_execution_metadata(
            {"namespace": namespace, "deployment_name": deployment_name},
            start_time,
        ),
    )


@tool_handler
def query_metrics_timeseries(
    promql_query: str,
    time_range: str = "1h",
    step: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Execute a Prometheus range query for time-series data.

    This is a raw access tool for custom investigations. The AI can write
    specific PromQL queries to investigate particular metrics.

    Args:
        promql_query: PromQL query string. Must be a valid Prometheus query.
            Common examples:
            - rate(container_cpu_usage_seconds_total{namespace="X"}[5m])
            - sum(container_memory_working_set_bytes{namespace="X"}) by (pod)
            - kube_pod_container_status_restarts_total{namespace="X"}
        time_range: How far back to query. Options: "1h", "6h", "24h", "7d".
        step: Query resolution step (e.g., "15s", "1m", "5m").
            If not provided, automatically calculated to return ~100 data points.
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - results: List of TimeseriesResult objects
        - query: The executed query (for reference)
        - data_points_per_series: Number of data points in each series

    Example:
        ```python
        # CPU usage over last hour
        result = query_metrics_timeseries(
            promql_query='sum(rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])) by (pod)',
            time_range="1h"
        )

        # Memory trend over 24h
        result = query_metrics_timeseries(
            promql_query='sum(container_memory_working_set_bytes{namespace="load-tester"}) by (pod)',
            time_range="24h",
            step="5m"
        )
        ```

    Note:
        Results are limited to prevent overwhelming the AI. Step size is
        automatically adjusted to return approximately 100 data points
        per series.
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    prom = PrometheusClient(settings)

    # Parse time range
    range_seconds = parse_duration(time_range)
    end = datetime.now(timezone.utc)
    start_dt = end - timedelta(seconds=range_seconds)

    # Execute query
    raw_results = prom.query_range(
        query=promql_query,
        start=start_dt,
        end=end,
        step=step,
    )

    # Convert to TimeseriesResult models
    results = []
    for r in raw_results:
        metric = r.get("metric", {})
        values = r.get("values", [])

        # Limit data points
        max_points = settings.max_timeseries_points
        if len(values) > max_points:
            # Sample evenly
            step_size = len(values) // max_points
            values = values[::step_size][:max_points]

        data_points = [
            TimeseriesDataPoint(
                timestamp=datetime.fromtimestamp(v[0], tz=timezone.utc),
                value=float(v[1]) if v[1] != "NaN" else 0.0,
            )
            for v in values
        ]

        # Determine metric name
        metric_name = metric.get("__name__", "query_result")

        result = TimeseriesResult(
            metric_name=metric_name,
            labels={k: v for k, v in metric.items() if k != "__name__"},
            data_points=data_points,
        )
        results.append(result)

    warnings = []
    if not results:
        warnings.append("Query returned no results. Check the query and namespace.")

    return ToolResponse(
        status=ToolStatus.SUCCESS if results else ToolStatus.PARTIAL,
        result={
            "results": [r.model_dump() for r in results],
            "query": promql_query,
            "series_count": len(results),
            "data_points_per_series": len(results[0].data_points) if results else 0,
        },
        warnings=warnings,
        metadata=add_execution_metadata(
            {"time_range": time_range, "step": step},
            start_time,
        ),
    )


@tool_handler
def get_resource_trends(
    namespace: str,
    deployment_name: str | None = None,
    metric_type: str = "cpu",
    period: str = "24h",
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get pre-computed resource usage trends with statistical analysis.

    Provides semantic summary of resource usage patterns including averages,
    percentiles, trend direction, and spike detection. This is more useful
    than raw time-series for understanding overall patterns.

    Args:
        namespace: Kubernetes namespace to query (required).
        deployment_name: Specific deployment to filter. If None, aggregates
            across all pods in the namespace.
        metric_type: Type of metric to analyze. Options:
            - "cpu": CPU usage in cores
            - "memory": Memory usage in bytes
            - "network_rx": Network receive bytes/sec
            - "network_tx": Network transmit bytes/sec
        period: Analysis period. Options: "1h", "6h", "24h", "7d", "30d".
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - trend: ResourceTrend object with statistics and analysis
        - interpretation: Human-readable interpretation of the trend

    Example:
        ```python
        # CPU trend over last 24h
        result = get_resource_trends(
            namespace="load-tester",
            deployment_name="local-backend",
            metric_type="cpu",
            period="24h"
        )

        # Memory trend over last week
        result = get_resource_trends(
            namespace="load-tester",
            metric_type="memory",
            period="7d"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    prom = PrometheusClient(settings)

    # Build query based on metric type
    if deployment_name:
        selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
    else:
        selector = f'namespace="{namespace}"'

    if metric_type == "cpu":
        query = f"sum(rate(container_cpu_usage_seconds_total{{{selector}}}[5m]))"
        unit = "cores"
    elif metric_type == "memory":
        query = f"sum(container_memory_working_set_bytes{{{selector}}})"
        unit = "bytes"
    elif metric_type == "network_rx":
        query = f"sum(rate(container_network_receive_bytes_total{{{selector}}}[5m]))"
        unit = "bytes/sec"
    elif metric_type == "network_tx":
        query = f"sum(rate(container_network_transmit_bytes_total{{{selector}}}[5m]))"
        unit = "bytes/sec"
    else:
        return ToolResponse.error(
            error_message=f"Invalid metric_type: {metric_type}. "
            f"Use 'cpu', 'memory', 'network_rx', or 'network_tx'.",
            error_type="ValidationError",
        )

    # Parse period and query
    period_seconds = parse_duration(period)
    end = datetime.now(timezone.utc)
    start_dt = end - timedelta(seconds=period_seconds)

    results = prom.query_range(query=query, start=start_dt, end=end)

    if not results or not results[0].get("values"):
        return ToolResponse.partial(
            result={
                "trend": None,
                "interpretation": "No data available for the specified period.",
            },
            warnings=[
                "No metric data found. The deployment may not exist or has no pods."
            ],
            metadata=add_execution_metadata(
                {
                    "namespace": namespace,
                    "deployment_name": deployment_name,
                    "metric_type": metric_type,
                },
                start_time,
            ),
        )

    # Extract values
    values = [float(v[1]) for v in results[0]["values"] if v[1] != "NaN"]
    timestamps = [
        datetime.fromtimestamp(v[0], tz=timezone.utc) for v in results[0]["values"]
    ]

    if len(values) < 2:
        return ToolResponse.partial(
            result={
                "trend": None,
                "interpretation": "Insufficient data points for trend analysis.",
            },
            warnings=["Need at least 2 data points for trend analysis."],
            metadata=add_execution_metadata({}, start_time),
        )

    # Calculate statistics
    values_array = np.array(values)
    avg = float(np.mean(values_array))
    minimum = float(np.min(values_array))
    maximum = float(np.max(values_array))
    p50 = float(np.percentile(values_array, 50))
    p95 = float(np.percentile(values_array, 95))
    p99 = float(np.percentile(values_array, 99))
    std_dev = float(np.std(values_array))

    # Calculate trend direction
    first_quarter = np.mean(values_array[: len(values_array) // 4])
    last_quarter = np.mean(values_array[-len(values_array) // 4 :])

    if first_quarter == 0:
        change_percent = 0 if last_quarter == 0 else 100
    else:
        change_percent = ((last_quarter - first_quarter) / first_quarter) * 100

    # Determine trend direction
    if abs(change_percent) < 10:
        trend_direction = TrendDirection.STABLE
    elif change_percent > 0:
        trend_direction = TrendDirection.INCREASING
    else:
        trend_direction = TrendDirection.DECREASING

    # Check for volatility
    cv = (std_dev / avg) if avg > 0 else 0  # Coefficient of variation
    if cv > 0.5:  # High variability
        trend_direction = TrendDirection.VOLATILE

    # Detect spikes (values > mean + 2*std_dev)
    spike_threshold = avg + 2 * std_dev
    spike_indices = np.where(values_array > spike_threshold)[0]
    spike_times = [timestamps[i] for i in spike_indices if i < len(timestamps)]

    trend = ResourceTrend(
        resource_type=metric_type,
        namespace=namespace,
        deployment_name=deployment_name,
        period=period,
        average=round(avg, 4),
        minimum=round(minimum, 4),
        maximum=round(maximum, 4),
        p50=round(p50, 4),
        p95=round(p95, 4),
        p99=round(p99, 4),
        std_dev=round(std_dev, 4),
        trend_direction=trend_direction,
        trend_change_percent=round(change_percent, 1),
        spike_count=len(spike_times),
        spike_times=spike_times[:10],  # Limit to 10 spike times
        unit=unit,
    )

    # Generate interpretation
    interpretation = f"{metric_type.upper()} usage is {trend_direction.value}"
    if trend_direction in (TrendDirection.INCREASING, TrendDirection.DECREASING):
        interpretation += f" ({change_percent:+.1f}% over {period})"
    if trend.spike_count > 0:
        interpretation += f". Detected {trend.spike_count} spike(s)."
    interpretation += f" Average: {avg:.4f} {unit}, P95: {p95:.4f} {unit}."

    return ToolResponse.success(
        result={
            "trend": trend.model_dump(),
            "interpretation": interpretation,
        },
        metadata=add_execution_metadata(
            {
                "namespace": namespace,
                "deployment_name": deployment_name,
                "metric_type": metric_type,
                "period": period,
            },
            start_time,
        ),
    )
