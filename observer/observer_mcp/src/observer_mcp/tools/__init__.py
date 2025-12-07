"""Tools package - Observability tool implementations."""

from observer_mcp.tools.analysis import (
    analyze_restart_patterns,
    compare_period_metrics,
    get_anomaly_report,
    get_deployment_history,
)
from observer_mcp.tools.discovery import (
    get_cluster_capacity,
    get_deployment_info,
    get_namespace_summary,
)
from observer_mcp.tools.health import (
    get_container_logs,
    get_pod_status,
    get_recent_events,
)
from observer_mcp.tools.metrics import (
    get_current_resource_usage,
    get_resource_trends,
    query_metrics_timeseries,
)

__all__ = [
    # Discovery tools
    "get_deployment_info",
    "get_namespace_summary",
    "get_cluster_capacity",
    # Health tools
    "get_pod_status",
    "get_recent_events",
    "get_container_logs",
    # Metrics tools
    "get_current_resource_usage",
    "query_metrics_timeseries",
    "get_resource_trends",
    # Analysis tools
    "analyze_restart_patterns",
    "get_deployment_history",
    "compare_period_metrics",
    "get_anomaly_report",
]
