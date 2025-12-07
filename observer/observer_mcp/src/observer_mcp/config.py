"""
Configuration management for Observer MCP.

Supports both in-cluster (service account) and local (kubeconfig) authentication.
Configuration is read from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.

    All settings can be configured via environment variables with the
    OBSERVER_ prefix (e.g., OBSERVER_PROMETHEUS_URL).

    Attributes:
        prometheus_url: Prometheus server URL. If not set, defaults to
            in-cluster service discovery URL.
        prometheus_bearer_token: Optional bearer token for Prometheus auth.
        kubeconfig_path: Path to kubeconfig file for local development.
            If not set, uses in-cluster config or default kubeconfig.
        kubernetes_context: Kubernetes context to use (optional).
        default_namespace: Default namespace for queries when not specified.
        max_log_lines: Maximum number of log lines to return (prevents overload).
        max_events: Maximum number of events to return.
        max_timeseries_points: Maximum data points in time-series queries.
        request_timeout_seconds: Timeout for API requests.
    """

    model_config = SettingsConfigDict(
        env_prefix="OBSERVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Prometheus configuration
    prometheus_url: str = "http://kube-prometheus-stack-prometheus.monitoring:9090"
    prometheus_bearer_token: str | None = None

    # Kubernetes configuration
    kubeconfig_path: str | None = None
    kubernetes_context: str | None = None

    # Default query parameters
    default_namespace: str = "default"

    # Output limits to prevent AI overload
    max_log_lines: int = 100
    max_events: int = 50
    max_timeseries_points: int = 100

    # Request configuration
    request_timeout_seconds: int = 30

    def is_in_cluster(self) -> bool:
        """Check if running inside a Kubernetes cluster."""
        import os

        return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()
