"""
Pydantic models for Prometheus metrics and time-series data.

These models provide structured representations of metrics data
optimized for AI consumption and analysis.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Direction of a metric trend over time."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class ResourceUsage(BaseModel):
    """Current resource usage for a pod or container."""

    pod_name: str = Field(description="Pod name")
    namespace: str = Field(description="Pod namespace")
    container_name: str | None = Field(
        default=None, description="Container name (if container-level metrics)"
    )
    cpu_usage_cores: float = Field(description="Current CPU usage in cores")
    cpu_usage_percent: float | None = Field(
        default=None, description="CPU usage as % of limit (if limit set)"
    )
    cpu_request_cores: float | None = Field(
        default=None, description="CPU request in cores"
    )
    cpu_limit_cores: float | None = Field(
        default=None, description="CPU limit in cores"
    )
    memory_usage_bytes: int = Field(description="Current memory usage in bytes")
    memory_usage_mb: float = Field(description="Current memory usage in MB")
    memory_usage_percent: float | None = Field(
        default=None, description="Memory usage as % of limit (if limit set)"
    )
    memory_request_bytes: int | None = Field(
        default=None, description="Memory request in bytes"
    )
    memory_limit_bytes: int | None = Field(
        default=None, description="Memory limit in bytes"
    )

    @property
    def is_cpu_throttled(self) -> bool:
        """Check if CPU usage is near or at limit."""
        if self.cpu_usage_percent is not None:
            return self.cpu_usage_percent >= 90
        return False

    @property
    def is_memory_pressure(self) -> bool:
        """Check if memory usage is high."""
        if self.memory_usage_percent is not None:
            return self.memory_usage_percent >= 80
        return False


class TimeseriesDataPoint(BaseModel):
    """A single data point in a time series."""

    timestamp: datetime = Field(description="Data point timestamp")
    value: float = Field(description="Metric value at this timestamp")


class TimeseriesResult(BaseModel):
    """Result of a Prometheus time-series query."""

    metric_name: str = Field(description="Prometheus metric name")
    labels: dict[str, str] = Field(default_factory=dict, description="Metric labels")
    data_points: list[TimeseriesDataPoint] = Field(
        description="Time-series data points"
    )

    @property
    def latest_value(self) -> float | None:
        """Get the most recent value."""
        if self.data_points:
            return self.data_points[-1].value
        return None

    @property
    def average(self) -> float | None:
        """Calculate average value across all data points."""
        if self.data_points:
            return sum(dp.value for dp in self.data_points) / len(self.data_points)
        return None


class ResourceTrend(BaseModel):
    """
    Statistical summary of resource usage over time.

    Pre-computed trends to help AI understand resource patterns
    without processing raw time-series data.
    """

    resource_type: str = Field(description="Type of resource (cpu, memory, network)")
    namespace: str = Field(description="Namespace")
    deployment_name: str | None = Field(
        default=None, description="Deployment name (if deployment-specific)"
    )
    period: str = Field(description="Time period analyzed (e.g., '24h', '7d')")

    # Statistical summary
    average: float = Field(description="Average value over period")
    minimum: float = Field(description="Minimum value over period")
    maximum: float = Field(description="Maximum value over period")
    p50: float = Field(description="50th percentile (median)")
    p95: float = Field(description="95th percentile")
    p99: float = Field(description="99th percentile")
    std_dev: float = Field(description="Standard deviation")

    # Trend analysis
    trend_direction: TrendDirection = Field(description="Overall trend direction")
    trend_change_percent: float = Field(description="% change from period start to end")

    # Anomaly detection
    spike_count: int = Field(
        default=0, description="Number of significant spikes detected"
    )
    spike_times: list[datetime] = Field(
        default_factory=list, description="Timestamps of detected spikes"
    )

    # Context
    unit: str = Field(
        default="", description="Unit of measurement (cores, bytes, etc.)"
    )


class MetricComparison(BaseModel):
    """Comparison of metrics between two time periods."""

    metric_name: str = Field(description="Metric being compared")
    namespace: str = Field(description="Namespace")
    deployment_name: str | None = Field(default=None, description="Deployment name")

    baseline_period: str = Field(description="Baseline period description")
    compare_period: str = Field(description="Comparison period description")

    baseline_average: float = Field(description="Average during baseline period")
    compare_average: float = Field(description="Average during comparison period")

    percent_change: float = Field(
        description="% change from baseline (positive = increase)"
    )
    is_significant: bool = Field(
        description="Whether change is statistically significant"
    )

    baseline_p95: float = Field(description="95th percentile during baseline")
    compare_p95: float = Field(description="95th percentile during comparison")

    notable_differences: list[str] = Field(
        default_factory=list, description="Human-readable notable differences"
    )


class AnomalyInfo(BaseModel):
    """Information about a detected anomaly."""

    anomaly_type: str = Field(
        description="Type of anomaly (traffic_spike, restart_pattern, resource_exhaustion)"
    )
    severity: str = Field(description="Severity level (low, medium, high, critical)")
    namespace: str = Field(description="Affected namespace")
    resource_name: str | None = Field(
        default=None, description="Affected resource name"
    )
    resource_kind: str | None = Field(
        default=None, description="Kind of affected resource (Pod, Deployment, etc.)"
    )

    detected_at: datetime = Field(description="When anomaly was detected")
    description: str = Field(description="Human-readable description")

    metric_name: str | None = Field(default=None, description="Related metric name")
    current_value: float | None = Field(
        default=None, description="Current metric value"
    )
    expected_range: tuple[float, float] | None = Field(
        default=None, description="Expected value range (min, max)"
    )

    recommendation: str | None = Field(
        default=None, description="Suggested action to address the anomaly"
    )
