"""
Prometheus API client wrapper.

Provides a simplified interface to Prometheus for querying metrics,
with support for both instant and range queries.
"""

from datetime import datetime
from typing import Any

import httpx

from observer_mcp.config import Settings, get_settings


class PrometheusClientError(Exception):
    """Base exception for Prometheus client errors."""

    pass


class PrometheusQueryError(PrometheusClientError):
    """Error executing a Prometheus query."""

    pass


class PrometheusClient:
    """
    Prometheus API client wrapper.

    Provides methods for querying Prometheus metrics with automatic
    handling of authentication and response parsing.

    Args:
        settings: Optional settings override. Uses default settings if not provided.

    Example:
        ```python
        client = PrometheusClient()

        # Instant query
        result = client.query('up{job="kubernetes-pods"}')

        # Range query
        result = client.query_range(
            query='rate(container_cpu_usage_seconds_total[5m])',
            start=datetime.now() - timedelta(hours=1),
            end=datetime.now(),
            step='1m'
        )
        ```
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._base_url = self._settings.prometheus_url.rstrip("/")
        self._timeout = self._settings.request_timeout_seconds

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers including authentication if configured."""
        headers = {"Accept": "application/json"}
        if self._settings.prometheus_bearer_token:
            headers["Authorization"] = (
                f"Bearer {self._settings.prometheus_bearer_token}"
            )
        return headers

    def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Make a request to the Prometheus API.

        Args:
            endpoint: API endpoint (e.g., '/api/v1/query').
            params: Query parameters.

        Returns:
            Parsed JSON response data.

        Raises:
            PrometheusClientError: If the request fails.
            PrometheusQueryError: If Prometheus returns an error.
        """
        url = f"{self._base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            raise PrometheusClientError(
                f"Prometheus API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise PrometheusClientError(
                f"Failed to connect to Prometheus at {self._base_url}: {e}"
            ) from e
        except Exception as e:
            raise PrometheusClientError(f"Unexpected error: {e}") from e

        if data.get("status") != "success":
            error_type = data.get("errorType", "unknown")
            error_msg = data.get("error", "Unknown error")
            raise PrometheusQueryError(f"Query failed ({error_type}): {error_msg}")

        return data.get("data", {})

    def query(self, query: str, time: datetime | None = None) -> list[dict[str, Any]]:
        """
        Execute an instant query.

        Args:
            query: PromQL query string.
            time: Evaluation timestamp (default: current time).

        Returns:
            List of result dictionaries with 'metric' and 'value' keys.

        Raises:
            PrometheusQueryError: If the query is invalid or fails.

        Example:
            ```python
            # Get current CPU usage
            results = client.query(
                'sum(rate(container_cpu_usage_seconds_total{namespace="default"}[5m])) by (pod)'
            )
            for r in results:
                print(f"{r['metric']['pod']}: {r['value'][1]}")
            ```
        """
        params: dict[str, Any] = {"query": query}
        if time:
            params["time"] = time.timestamp()

        data = self._make_request("/api/v1/query", params)
        return data.get("result", [])

    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a range query.

        Args:
            query: PromQL query string.
            start: Start timestamp.
            end: End timestamp.
            step: Query resolution step (e.g., '15s', '1m', '5m').
                  If not provided, automatically calculated based on time range.

        Returns:
            List of result dictionaries with 'metric' and 'values' keys.
            Values is a list of [timestamp, value] pairs.

        Raises:
            PrometheusQueryError: If the query is invalid or fails.

        Example:
            ```python
            # CPU usage over last hour
            results = client.query_range(
                query='rate(container_cpu_usage_seconds_total[5m])',
                start=datetime.now() - timedelta(hours=1),
                end=datetime.now(),
                step='1m'
            )
            ```
        """
        if step is None:
            step = self._calculate_step(start, end)

        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }

        data = self._make_request("/api/v1/query_range", params)
        return data.get("result", [])

    def _calculate_step(self, start: datetime, end: datetime) -> str:
        """
        Calculate an appropriate step size based on time range.

        Aims to return approximately max_timeseries_points data points.

        Args:
            start: Start timestamp.
            end: End timestamp.

        Returns:
            Step string (e.g., '15s', '1m', '5m').
        """
        duration = end - start
        total_seconds = duration.total_seconds()
        max_points = self._settings.max_timeseries_points

        step_seconds = max(15, int(total_seconds / max_points))

        if step_seconds < 60:
            return f"{step_seconds}s"
        elif step_seconds < 3600:
            return f"{step_seconds // 60}m"
        else:
            return f"{step_seconds // 3600}h"

    def get_metric_names(self, match: str | None = None) -> list[str]:
        """
        Get list of metric names.

        Args:
            match: Optional regex to filter metric names.

        Returns:
            List of metric names.
        """
        params = {}
        if match:
            params["match[]"] = match

        try:
            data = self._make_request("/api/v1/label/__name__/values", params)
            return data if isinstance(data, list) else []
        except PrometheusClientError:
            # Some Prometheus versions don't support this endpoint
            return []

    def get_label_values(self, label: str, match: str | None = None) -> list[str]:
        """
        Get all values for a specific label.

        Args:
            label: Label name.
            match: Optional series selector to filter.

        Returns:
            List of label values.
        """
        params = {}
        if match:
            params["match[]"] = match

        data = self._make_request(f"/api/v1/label/{label}/values", params)
        return data if isinstance(data, list) else []

    def check_health(self) -> bool:
        """
        Check if Prometheus is healthy and reachable.

        Returns:
            True if Prometheus is healthy, False otherwise.
        """
        try:
            url = f"{self._base_url}/-/healthy"
            with httpx.Client(timeout=5) as client:
                response = client.get(url, headers=self._get_headers())
                return response.status_code == 200
        except Exception:
            return False

    # =========================================================================
    # Common Pre-built Queries
    # =========================================================================

    def get_container_cpu_usage(
        self,
        namespace: str,
        deployment_name: str | None = None,
        duration: str = "5m",
    ) -> list[dict[str, Any]]:
        """
        Get CPU usage rate for containers.

        Args:
            namespace: Kubernetes namespace.
            deployment_name: Optional specific deployment to filter.
            duration: Rate calculation window (default: 5m).

        Returns:
            List of results with pod and container labels.
        """
        if deployment_name:
            selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
        else:
            selector = f'namespace="{namespace}"'

        query = f"sum(rate(container_cpu_usage_seconds_total{{{selector}}}[{duration}])) by (pod, container)"
        return self.query(query)

    def get_container_memory_usage(
        self,
        namespace: str,
        deployment_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get current memory usage for containers.

        Args:
            namespace: Kubernetes namespace.
            deployment_name: Optional specific deployment to filter.

        Returns:
            List of results with pod and container labels.
        """
        if deployment_name:
            selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
        else:
            selector = f'namespace="{namespace}"'

        query = (
            f"sum(container_memory_working_set_bytes{{{selector}}}) by (pod, container)"
        )
        return self.query(query)

    def get_pod_restart_count(
        self,
        namespace: str,
        deployment_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get pod restart counts.

        Args:
            namespace: Kubernetes namespace.
            deployment_name: Optional specific deployment to filter.

        Returns:
            List of results with pod labels.
        """
        if deployment_name:
            selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
        else:
            selector = f'namespace="{namespace}"'

        query = f"sum(kube_pod_container_status_restarts_total{{{selector}}}) by (pod)"
        return self.query(query)

    def get_resource_limits(
        self,
        namespace: str,
        deployment_name: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get resource requests and limits for containers.

        Args:
            namespace: Kubernetes namespace.
            deployment_name: Optional specific deployment to filter.

        Returns:
            Dictionary with cpu_requests, cpu_limits, memory_requests, memory_limits.
        """
        if deployment_name:
            selector = f'namespace="{namespace}", pod=~"{deployment_name}.*"'
        else:
            selector = f'namespace="{namespace}"'

        return {
            "cpu_requests": self.query(
                f"sum(kube_pod_container_resource_requests{{resource='cpu', {selector}}}) by (pod, container)"
            ),
            "cpu_limits": self.query(
                f"sum(kube_pod_container_resource_limits{{resource='cpu', {selector}}}) by (pod, container)"
            ),
            "memory_requests": self.query(
                f"sum(kube_pod_container_resource_requests{{resource='memory', {selector}}}) by (pod, container)"
            ),
            "memory_limits": self.query(
                f"sum(kube_pod_container_resource_limits{{resource='memory', {selector}}}) by (pod, container)"
            ),
        }
