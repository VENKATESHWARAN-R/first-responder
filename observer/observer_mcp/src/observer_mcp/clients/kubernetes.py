"""
Kubernetes API client wrapper.

Provides a simplified interface to the Kubernetes API with support for
both in-cluster (service account) and local (kubeconfig) authentication.
"""

from datetime import datetime, timezone
from functools import cached_property

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from observer_mcp.config import Settings, get_settings


class K8sClientError(Exception):
    """Base exception for Kubernetes client errors."""

    pass


class K8sNotFoundError(K8sClientError):
    """Resource not found in the cluster."""

    pass


class K8sClient:
    """
    Kubernetes API client wrapper.

    Automatically handles authentication using either in-cluster service
    account credentials or a local kubeconfig file.

    Args:
        settings: Optional settings override. Uses default settings if not provided.

    Example:
        ```python
        client = K8sClient()

        # List deployments
        deployments = client.list_deployments(namespace="default")

        # Get specific pod
        pod = client.get_pod(namespace="default", name="my-pod")
        ```
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._load_config()

    def _load_config(self) -> None:
        """Load Kubernetes configuration."""
        try:
            if self._settings.is_in_cluster():
                config.load_incluster_config()
            elif self._settings.kubeconfig_path:
                config.load_kube_config(
                    config_file=self._settings.kubeconfig_path,
                    context=self._settings.kubernetes_context,
                )
            else:
                config.load_kube_config(context=self._settings.kubernetes_context)
        except Exception as e:
            raise K8sClientError(f"Failed to load Kubernetes config: {e}") from e

    @cached_property
    def core_v1(self) -> client.CoreV1Api:
        """Core V1 API client."""
        return client.CoreV1Api()

    @cached_property
    def apps_v1(self) -> client.AppsV1Api:
        """Apps V1 API client."""
        return client.AppsV1Api()

    # =========================================================================
    # Deployment Methods
    # =========================================================================

    def list_deployments(
        self,
        namespace: str | None = None,
        label_selector: str | None = None,
    ) -> list[client.V1Deployment]:
        """
        List deployments in a namespace or across all namespaces.

        Args:
            namespace: Namespace to query. If None, queries all namespaces.
            label_selector: Optional label selector (e.g., "app=backend").

        Returns:
            List of V1Deployment objects.

        Raises:
            K8sClientError: If the API call fails.
        """
        try:
            if namespace:
                result = self.apps_v1.list_namespaced_deployment(
                    namespace=namespace,
                    label_selector=label_selector,
                )
            else:
                result = self.apps_v1.list_deployment_for_all_namespaces(
                    label_selector=label_selector,
                )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list deployments: {e.reason}") from e

    def get_deployment(
        self,
        namespace: str,
        name: str,
    ) -> client.V1Deployment:
        """
        Get a specific deployment.

        Args:
            namespace: Deployment namespace.
            name: Deployment name.

        Returns:
            V1Deployment object.

        Raises:
            K8sNotFoundError: If deployment doesn't exist.
            K8sClientError: If the API call fails.
        """
        try:
            return self.apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace,
            )
        except ApiException as e:
            if e.status == 404:
                raise K8sNotFoundError(
                    f"Deployment '{name}' not found in namespace '{namespace}'"
                ) from e
            raise K8sClientError(f"Failed to get deployment: {e.reason}") from e

    def list_replica_sets(
        self,
        namespace: str,
        label_selector: str | None = None,
    ) -> list[client.V1ReplicaSet]:
        """
        List ReplicaSets in a namespace.

        Args:
            namespace: Namespace to query.
            label_selector: Optional label selector.

        Returns:
            List of V1ReplicaSet objects.
        """
        try:
            result = self.apps_v1.list_namespaced_replica_set(
                namespace=namespace,
                label_selector=label_selector,
            )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list replica sets: {e.reason}") from e

    # =========================================================================
    # Pod Methods
    # =========================================================================

    def list_pods(
        self,
        namespace: str | None = None,
        label_selector: str | None = None,
        field_selector: str | None = None,
    ) -> list[client.V1Pod]:
        """
        List pods in a namespace or across all namespaces.

        Args:
            namespace: Namespace to query. If None, queries all namespaces.
            label_selector: Optional label selector (e.g., "app=backend").
            field_selector: Optional field selector (e.g., "status.phase=Running").

        Returns:
            List of V1Pod objects.
        """
        try:
            if namespace:
                result = self.core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                result = self.core_v1.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list pods: {e.reason}") from e

    def get_pod(self, namespace: str, name: str) -> client.V1Pod:
        """
        Get a specific pod.

        Args:
            namespace: Pod namespace.
            name: Pod name.

        Returns:
            V1Pod object.

        Raises:
            K8sNotFoundError: If pod doesn't exist.
        """
        try:
            return self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
        except ApiException as e:
            if e.status == 404:
                raise K8sNotFoundError(
                    f"Pod '{name}' not found in namespace '{namespace}'"
                ) from e
            raise K8sClientError(f"Failed to get pod: {e.reason}") from e

    def get_pod_logs(
        self,
        namespace: str,
        name: str,
        container: str | None = None,
        tail_lines: int = 100,
        since_seconds: int | None = None,
        previous: bool = False,
    ) -> str:
        """
        Get logs from a pod.

        Args:
            namespace: Pod namespace.
            name: Pod name.
            container: Container name (required for multi-container pods).
            tail_lines: Number of lines to return from the end.
            since_seconds: Only return logs newer than this many seconds.
            previous: If True, get logs from previous container instance.

        Returns:
            Log content as string.

        Raises:
            K8sNotFoundError: If pod doesn't exist.
            K8sClientError: If the API call fails.
        """
        try:
            return self.core_v1.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                since_seconds=since_seconds,
                previous=previous,
            )
        except ApiException as e:
            if e.status == 404:
                raise K8sNotFoundError(
                    f"Pod '{name}' not found in namespace '{namespace}'"
                ) from e
            raise K8sClientError(f"Failed to get pod logs: {e.reason}") from e

    # =========================================================================
    # Event Methods
    # =========================================================================

    def list_events(
        self,
        namespace: str | None = None,
        field_selector: str | None = None,
        limit: int | None = None,
    ) -> list[client.CoreV1Event]:
        """
        List events in a namespace or across all namespaces.

        Args:
            namespace: Namespace to query. If None, queries all namespaces.
            field_selector: Optional field selector.
            limit: Maximum number of events to return.

        Returns:
            List of CoreV1Event objects, sorted by last timestamp descending.
        """
        try:
            if namespace:
                result = self.core_v1.list_namespaced_event(
                    namespace=namespace,
                    field_selector=field_selector,
                    limit=limit,
                )
            else:
                result = self.core_v1.list_event_for_all_namespaces(
                    field_selector=field_selector,
                    limit=limit,
                )

            # Sort by last timestamp, most recent first
            events = result.items
            events.sort(
                key=lambda e: e.last_timestamp
                or e.event_time
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            return events
        except ApiException as e:
            raise K8sClientError(f"Failed to list events: {e.reason}") from e

    # =========================================================================
    # Node Methods
    # =========================================================================

    def list_nodes(
        self,
        label_selector: str | None = None,
    ) -> list[client.V1Node]:
        """
        List all nodes in the cluster.

        Args:
            label_selector: Optional label selector.

        Returns:
            List of V1Node objects.
        """
        try:
            result = self.core_v1.list_node(label_selector=label_selector)
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list nodes: {e.reason}") from e

    # =========================================================================
    # Namespace Methods
    # =========================================================================

    def list_namespaces(self) -> list[client.V1Namespace]:
        """
        List all namespaces.

        Returns:
            List of V1Namespace objects.
        """
        try:
            result = self.core_v1.list_namespace()
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list namespaces: {e.reason}") from e

    # =========================================================================
    # Service Methods
    # =========================================================================

    def list_services(
        self,
        namespace: str | None = None,
        label_selector: str | None = None,
    ) -> list[client.V1Service]:
        """
        List services in a namespace or across all namespaces.

        Args:
            namespace: Namespace to query. If None, queries all namespaces.
            label_selector: Optional label selector.

        Returns:
            List of V1Service objects.
        """
        try:
            if namespace:
                result = self.core_v1.list_namespaced_service(
                    namespace=namespace,
                    label_selector=label_selector,
                )
            else:
                result = self.core_v1.list_service_for_all_namespaces(
                    label_selector=label_selector,
                )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list services: {e.reason}") from e

    # =========================================================================
    # ConfigMap & Secret Methods
    # =========================================================================

    def list_configmaps(
        self,
        namespace: str,
        label_selector: str | None = None,
    ) -> list[client.V1ConfigMap]:
        """
        List ConfigMaps in a namespace.

        Args:
            namespace: Namespace to query.
            label_selector: Optional label selector.

        Returns:
            List of V1ConfigMap objects.
        """
        try:
            result = self.core_v1.list_namespaced_config_map(
                namespace=namespace,
                label_selector=label_selector,
            )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list configmaps: {e.reason}") from e

    def list_secrets(
        self,
        namespace: str,
        label_selector: str | None = None,
    ) -> list[client.V1Secret]:
        """
        List Secrets in a namespace (names only, not values).

        Args:
            namespace: Namespace to query.
            label_selector: Optional label selector.

        Returns:
            List of V1Secret objects.
        """
        try:
            result = self.core_v1.list_namespaced_secret(
                namespace=namespace,
                label_selector=label_selector,
            )
            return result.items
        except ApiException as e:
            raise K8sClientError(f"Failed to list secrets: {e.reason}") from e

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def get_pods_for_deployment(
        self,
        namespace: str,
        deployment_name: str,
    ) -> list[client.V1Pod]:
        """
        Get all pods belonging to a deployment.

        Args:
            namespace: Deployment namespace.
            deployment_name: Deployment name.

        Returns:
            List of pods matching the deployment's selector.
        """
        deployment = self.get_deployment(namespace, deployment_name)
        selector = deployment.spec.selector.match_labels
        label_selector = ",".join(f"{k}={v}" for k, v in selector.items())
        return self.list_pods(namespace=namespace, label_selector=label_selector)
