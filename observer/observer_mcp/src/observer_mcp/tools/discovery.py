"""
Resource Discovery Tools.

Tools for discovering and listing Kubernetes resources.
"""

from datetime import datetime

from observer_mcp.clients.kubernetes import K8sClient
from observer_mcp.config import Settings, get_settings
from observer_mcp.models.kubernetes import (
    ClusterCapacity,
    DeploymentInfo,
    NamespaceSummary,
    NodeInfo,
    ReplicaStatus,
)
from observer_mcp.models.responses import ToolResponse, add_execution_metadata
from observer_mcp.tools.base import tool_handler


@tool_handler
def get_deployment_info(
    namespace: str | None = None,
    deployment_name: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get information about Kubernetes deployments.

    Retrieves deployment details including name, namespace, container images,
    replica status, labels, and creation time. Use this to answer questions like
    "what version is running" or "what's deployed in namespace X".

    Args:
        namespace: Kubernetes namespace to query. If None, queries all namespaces.
        deployment_name: Specific deployment name to retrieve. If None, lists all
            deployments in the namespace(s).
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - deployments: List of DeploymentInfo objects
        - total_count: Total number of deployments found
        - healthy_count: Number of deployments with all replicas ready

    Example:
        ```python
        # Get all deployments in load-tester namespace
        result = get_deployment_info(namespace="load-tester")

        # Get specific deployment
        result = get_deployment_info(
            namespace="load-tester",
            deployment_name="local-backend"
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    if deployment_name and namespace:
        # Get specific deployment
        deployment = k8s.get_deployment(namespace, deployment_name)
        deployments = [deployment]
    else:
        # List deployments
        deployments = k8s.list_deployments(namespace=namespace)

    # Convert to DeploymentInfo models
    deployment_infos = []
    for dep in deployments:
        # Extract images from containers
        containers = dep.spec.template.spec.containers
        images = [c.image for c in containers]
        primary_image = images[0] if images else "unknown"

        # Build replica status
        status = dep.status
        replicas = ReplicaStatus(
            desired=dep.spec.replicas or 0,
            ready=status.ready_replicas or 0,
            available=status.available_replicas or 0,
            unavailable=status.unavailable_replicas or 0,
        )

        # Extract conditions
        conditions = []
        if status.conditions:
            for cond in status.conditions:
                conditions.append(
                    {
                        "type": cond.type,
                        "status": cond.status,
                        "reason": cond.reason or "",
                        "message": cond.message or "",
                    }
                )

        info = DeploymentInfo(
            name=dep.metadata.name,
            namespace=dep.metadata.namespace,
            replicas=replicas,
            image=primary_image,
            images=images,
            created_at=dep.metadata.creation_timestamp,
            labels=dep.metadata.labels or {},
            selector=dep.spec.selector.match_labels or {},
            strategy=dep.spec.strategy.type if dep.spec.strategy else "RollingUpdate",
            conditions=conditions,
        )
        deployment_infos.append(info)

    # Count healthy deployments
    healthy_count = sum(1 for d in deployment_infos if d.is_healthy)

    return ToolResponse.success(
        result={
            "deployments": [d.model_dump() for d in deployment_infos],
            "total_count": len(deployment_infos),
            "healthy_count": healthy_count,
        },
        metadata=add_execution_metadata(
            {"namespace": namespace or "all", "deployment_name": deployment_name},
            start_time,
        ),
    )


@tool_handler
def get_namespace_summary(
    namespace: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get a summary of resources in one or all namespaces.

    Provides an overview including pod counts, deployment counts, service counts,
    and a health score based on pod status and restarts. Useful for answering
    "what's the state of the cluster" or "how healthy is namespace X".

    Args:
        namespace: Specific namespace to summarize. If None, returns summary
            for all namespaces.
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - namespaces: List of NamespaceSummary objects
        - total_namespaces: Total namespace count
        - cluster_health_score: Average health score across all namespaces

    Example:
        ```python
        # Get summary for all namespaces
        result = get_namespace_summary()

        # Get specific namespace summary
        result = get_namespace_summary(namespace="load-tester")
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    # Get namespaces to query
    if namespace:
        namespaces_to_query = [namespace]
    else:
        ns_list = k8s.list_namespaces()
        namespaces_to_query = [ns.metadata.name for ns in ns_list]

    summaries = []

    for ns in namespaces_to_query:
        # Count resources
        pods = k8s.list_pods(namespace=ns)
        deployments = k8s.list_deployments(namespace=ns)
        services = k8s.list_services(namespace=ns)
        configmaps = k8s.list_configmaps(namespace=ns)
        secrets = k8s.list_secrets(namespace=ns)

        # Calculate stats
        running_pods = sum(1 for p in pods if p.status.phase == "Running")
        total_restarts = 0
        for pod in pods:
            if pod.status.container_statuses:
                total_restarts += sum(
                    cs.restart_count for cs in pod.status.container_statuses
                )

        # Calculate health score (0-1)
        # Based on: % running pods and restart rate
        if len(pods) > 0:
            running_ratio = running_pods / len(pods)
            restart_penalty = min(1.0, total_restarts * 0.05)  # 5% penalty per restart
            health_score = max(0, running_ratio - restart_penalty)
        else:
            health_score = 1.0  # Empty namespace is "healthy"

        # Get namespace labels
        ns_obj = next((n for n in k8s.list_namespaces() if n.metadata.name == ns), None)
        ns_labels = ns_obj.metadata.labels if ns_obj and ns_obj.metadata.labels else {}

        summary = NamespaceSummary(
            name=ns,
            pod_count=len(pods),
            running_pods=running_pods,
            deployment_count=len(deployments),
            service_count=len(services),
            configmap_count=len(configmaps),
            secret_count=len(secrets),
            total_restarts=total_restarts,
            health_score=round(health_score, 2),
            labels=ns_labels,
        )
        summaries.append(summary)

    # Calculate cluster-wide health score
    if summaries:
        cluster_health = sum(s.health_score for s in summaries) / len(summaries)
    else:
        cluster_health = 1.0

    return ToolResponse.success(
        result={
            "namespaces": [s.model_dump() for s in summaries],
            "total_namespaces": len(summaries),
            "cluster_health_score": round(cluster_health, 2),
        },
        metadata=add_execution_metadata(
            {"namespace": namespace or "all"},
            start_time,
        ),
    )


@tool_handler
def get_cluster_capacity(
    node_selector: str | None = None,
    settings: Settings | None = None,
) -> ToolResponse:
    """
    Get cluster capacity and node information.

    Provides total cluster resources, allocatable capacity, and per-node details.
    Use this to understand if the cluster itself is resource-constrained.

    Args:
        node_selector: Optional label selector to filter nodes
            (e.g., "node-role.kubernetes.io/worker=").
        settings: Optional settings override for testing.

    Returns:
        ToolResponse with result containing:
        - cluster: ClusterCapacity object with totals
        - node_count: Total number of nodes
        - nodes_ready: Number of Ready nodes

    Example:
        ```python
        # Get full cluster capacity
        result = get_cluster_capacity()

        # Get only worker nodes
        result = get_cluster_capacity(
            node_selector="node-role.kubernetes.io/worker="
        )
        ```
    """
    start_time = datetime.now()
    settings = settings or get_settings()
    k8s = K8sClient(settings)

    nodes = k8s.list_nodes(label_selector=node_selector)

    # Aggregate totals
    total_cpu = 0.0
    total_memory = 0
    allocatable_cpu = 0.0
    allocatable_memory = 0
    nodes_ready = 0

    node_infos = []

    for node in nodes:
        # Get capacity and allocatable
        capacity = node.status.capacity
        allocatable = node.status.allocatable

        cpu_cap = capacity.get("cpu", "0")
        mem_cap = capacity.get("memory", "0")
        cpu_alloc = allocatable.get("cpu", "0")
        mem_alloc = allocatable.get("memory", "0")

        # Parse CPU (can be "4" or "4000m")
        def parse_cpu(val: str) -> float:
            if val.endswith("m"):
                return float(val[:-1]) / 1000
            return float(val)

        # Parse memory (Ki, Mi, Gi suffixes)
        def parse_memory(val: str) -> int:
            val = val.strip()
            if val.endswith("Ki"):
                return int(val[:-2]) * 1024
            elif val.endswith("Mi"):
                return int(val[:-2]) * 1024 * 1024
            elif val.endswith("Gi"):
                return int(val[:-2]) * 1024 * 1024 * 1024
            elif val.endswith("Ti"):
                return int(val[:-2]) * 1024 * 1024 * 1024 * 1024
            return int(val)

        total_cpu += parse_cpu(cpu_cap)
        total_memory += parse_memory(mem_cap)
        allocatable_cpu += parse_cpu(cpu_alloc)
        allocatable_memory += parse_memory(mem_alloc)

        # Check node conditions
        conditions = {}
        is_ready = False
        for cond in node.status.conditions or []:
            conditions[cond.type] = cond.status == "True"
            if cond.type == "Ready" and cond.status == "True":
                is_ready = True
                nodes_ready += 1

        # Get node roles from labels
        roles = []
        for label_key in node.metadata.labels or {}:
            if label_key.startswith("node-role.kubernetes.io/"):
                roles.append(label_key.split("/")[1])
        if not roles:
            roles = ["worker"]

        # Count pods on this node
        pods = k8s.list_pods(field_selector=f"spec.nodeName={node.metadata.name}")

        node_info = NodeInfo(
            name=node.metadata.name,
            roles=roles,
            ready=is_ready,
            cpu_capacity=cpu_cap,
            memory_capacity=mem_cap,
            cpu_allocatable=cpu_alloc,
            memory_allocatable=mem_alloc,
            pod_count=len(pods),
            conditions=conditions,
            labels=node.metadata.labels or {},
        )
        node_infos.append(node_info)

    # Format totals
    def format_memory(b: int) -> str:
        return f"{b / (1024**3):.2f}Gi"

    capacity = ClusterCapacity(
        node_count=len(nodes),
        nodes_ready=nodes_ready,
        total_cpu=f"{total_cpu:.1f}",
        total_memory=format_memory(total_memory),
        allocatable_cpu=f"{allocatable_cpu:.1f}",
        allocatable_memory=format_memory(allocatable_memory),
        nodes=node_infos,
    )

    return ToolResponse.success(
        result={
            "cluster": capacity.model_dump(),
            "node_count": len(nodes),
            "nodes_ready": nodes_ready,
        },
        metadata=add_execution_metadata(
            {"node_selector": node_selector or "all"},
            start_time,
        ),
    )
