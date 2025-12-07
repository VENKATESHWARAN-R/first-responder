# Observer MCP - Kubernetes Observability Tooling

A Python library providing structured tools for AI-powered Kubernetes cluster observability. Designed for use with MCP (Model Context Protocol) servers.

## Features

- **13 Observability Tools** across 4 categories
- **Consistent Response Format** - All tools return `ToolResponse` with status, result, errors, warnings
- **AI-Friendly Output** - Pre-processed data with limits to prevent overload
- **Comprehensive Docstrings** - Every function documented for AI tool discovery
- **Dual Authentication** - Service account (in-cluster) or kubeconfig (local dev)

## Installation

```bash
# Using uv
cd observer/observer_mcp
uv sync

# For development
uv sync --extra dev
```

## Configuration

Configure via environment variables (prefix: `OBSERVER_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSERVER_PROMETHEUS_URL` | `http://kube-prometheus-stack-prometheus.monitoring:9090` | Prometheus server URL |
| `OBSERVER_PROMETHEUS_BEARER_TOKEN` | None | Optional bearer token for auth |
| `OBSERVER_KUBECONFIG_PATH` | None | Path to kubeconfig (local dev only) |
| `OBSERVER_MAX_LOG_LINES` | 100 | Max log lines per request |
| `OBSERVER_MAX_EVENTS` | 50 | Max events per request |

## Available Tools

### Discovery Tools

| Tool | Description |
|------|-------------|
| `get_deployment_info` | List deployments with images, replicas, labels |
| `get_namespace_summary` | Summary of resources per namespace with health score |
| `get_cluster_capacity` | Cluster capacity, node health, resource totals |

### Health Tools

| Tool | Description |
|------|-------------|
| `get_pod_status` | Pod states, restarts, container details |
| `get_recent_events` | K8s events (OOMKill, ImagePull errors, etc.) |
| `get_container_logs` | Container logs with truncation |

### Metrics Tools

| Tool | Description |
|------|-------------|
| `get_current_resource_usage` | Current CPU/memory with % of limits |
| `query_metrics_timeseries` | Raw PromQL range queries |
| `get_resource_trends` | Pre-computed trends with statistics |

### Analysis Tools

| Tool | Description |
|------|-------------|
| `analyze_restart_patterns` | Crash reasons, frequency patterns |
| `get_deployment_history` | Rollout history, image changes |
| `compare_period_metrics` | Compare metrics between periods |
| `get_anomaly_report` | Detect spikes, restarts, resource issues |

## Usage

```python
from observer_mcp.tools import (
    get_deployment_info,
    get_pod_status,
    get_current_resource_usage,
    analyze_restart_patterns,
)

# Get all deployments in a namespace
result = get_deployment_info(namespace="load-tester")
print(result.status)  # ToolStatus.SUCCESS
print(result.result)  # {"deployments": [...], "total_count": 2}

# Get pod health status
result = get_pod_status(
    namespace="load-tester",
    deployment_name="local-backend"
)

# Get current resource usage from Prometheus
result = get_current_resource_usage(
    namespace="load-tester",
    deployment_name="local-backend"
)

# Analyze restart patterns
result = analyze_restart_patterns(
    namespace="load-tester",
    deployment_name="local-backend",
    lookback_period="24h"
)
```

## Response Format

All tools return a `ToolResponse`:

```python
{
    "status": "success",           # success | partial | error
    "result": { ... },             # Tool-specific data
    "error": null,                 # Error message if status=error
    "warnings": [],                # Non-fatal issues
    "metadata": {
        "execution_time_ms": 45,
        "timestamp": "2025-12-08T00:00:00Z",
        ...
    }
}
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Type checking
uv run mypy src/

# Format
uv run ruff format src/
```

## License

MIT
