"""
Pydantic models for Kubernetes resources.

These models provide structured, typed representations of Kubernetes
resources optimized for AI consumption.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PodPhase(str, Enum):
    """Kubernetes pod phase states."""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class ContainerState(str, Enum):
    """Container runtime states."""

    RUNNING = "Running"
    WAITING = "Waiting"
    TERMINATED = "Terminated"


class ReplicaStatus(BaseModel):
    """Replica count status for a deployment or replicaset."""

    desired: int = Field(description="Desired number of replicas")
    ready: int = Field(description="Number of ready replicas")
    available: int = Field(description="Number of available replicas")
    unavailable: int = Field(default=0, description="Number of unavailable replicas")


class ContainerInfo(BaseModel):
    """Information about a container within a pod."""

    name: str = Field(description="Container name")
    image: str = Field(description="Container image with tag")
    state: ContainerState = Field(description="Current container state")
    ready: bool = Field(description="Whether container is ready")
    restart_count: int = Field(description="Number of restarts")
    last_restart_reason: str | None = Field(
        default=None, description="Reason for last restart (e.g., OOMKilled, Error)"
    )
    resources: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Resource requests and limits"
    )


class PodInfo(BaseModel):
    """Detailed information about a Kubernetes pod."""

    name: str = Field(description="Pod name")
    namespace: str = Field(description="Pod namespace")
    phase: PodPhase = Field(description="Pod phase (Running, Pending, etc.)")
    node: str | None = Field(default=None, description="Node the pod is running on")
    ip: str | None = Field(default=None, description="Pod IP address")
    created_at: datetime = Field(description="Pod creation timestamp")
    containers: list[ContainerInfo] = Field(description="Container information")
    total_restart_count: int = Field(description="Sum of all container restarts")
    labels: dict[str, str] = Field(default_factory=dict, description="Pod labels")

    @property
    def is_healthy(self) -> bool:
        """Check if pod is in a healthy state."""
        return self.phase == PodPhase.RUNNING and all(c.ready for c in self.containers)


class PodStatus(BaseModel):
    """Aggregated status for pods matching a selector."""

    total_pods: int = Field(description="Total number of pods")
    running: int = Field(description="Pods in Running phase")
    pending: int = Field(description="Pods in Pending phase")
    failed: int = Field(description="Pods in Failed phase")
    total_restarts: int = Field(description="Total restart count across all pods")
    pods: list[PodInfo] = Field(description="Individual pod details")


class DeploymentInfo(BaseModel):
    """Information about a Kubernetes deployment."""

    name: str = Field(description="Deployment name")
    namespace: str = Field(description="Deployment namespace")
    replicas: ReplicaStatus = Field(description="Replica status")
    image: str = Field(description="Primary container image:tag")
    images: list[str] = Field(
        default_factory=list, description="All container images in the deployment"
    )
    created_at: datetime = Field(description="Deployment creation timestamp")
    labels: dict[str, str] = Field(
        default_factory=dict, description="Deployment labels"
    )
    selector: dict[str, str] = Field(
        default_factory=dict, description="Pod selector labels"
    )
    strategy: str = Field(
        default="RollingUpdate",
        description="Deployment strategy (RollingUpdate, Recreate)",
    )
    conditions: list[dict[str, str]] = Field(
        default_factory=list, description="Deployment conditions"
    )

    @property
    def is_healthy(self) -> bool:
        """Check if deployment is healthy (all replicas ready)."""
        return self.replicas.ready >= self.replicas.desired


class EventSeverity(str, Enum):
    """Kubernetes event severity levels."""

    NORMAL = "Normal"
    WARNING = "Warning"


class EventInfo(BaseModel):
    """Kubernetes event information."""

    name: str = Field(description="Event name")
    namespace: str = Field(description="Event namespace")
    type: EventSeverity = Field(description="Event type (Normal/Warning)")
    reason: str = Field(description="Event reason code (e.g., Pulled, OOMKilled)")
    message: str = Field(description="Human-readable event message")
    involved_object: dict[str, str] = Field(
        description="Object this event is about (kind, name)"
    )
    first_seen: datetime = Field(description="First occurrence timestamp")
    last_seen: datetime = Field(description="Most recent occurrence timestamp")
    count: int = Field(default=1, description="Number of occurrences")
    source: str = Field(description="Component that generated the event")


class NodeInfo(BaseModel):
    """Information about a Kubernetes node."""

    name: str = Field(description="Node name")
    roles: list[str] = Field(description="Node roles (control-plane, worker)")
    ready: bool = Field(description="Whether node is Ready")
    cpu_capacity: str = Field(description="Total CPU capacity (e.g., '4')")
    memory_capacity: str = Field(description="Total memory capacity (e.g., '8Gi')")
    cpu_allocatable: str = Field(description="Allocatable CPU")
    memory_allocatable: str = Field(description="Allocatable memory")
    pod_count: int = Field(description="Number of pods on this node")
    conditions: dict[str, bool] = Field(
        default_factory=dict,
        description="Node conditions (Ready, MemoryPressure, etc.)",
    )
    labels: dict[str, str] = Field(default_factory=dict, description="Node labels")


class ClusterCapacity(BaseModel):
    """Cluster-wide capacity and resource information."""

    node_count: int = Field(description="Total number of nodes")
    nodes_ready: int = Field(description="Number of Ready nodes")
    total_cpu: str = Field(description="Total cluster CPU capacity")
    total_memory: str = Field(description="Total cluster memory capacity")
    allocatable_cpu: str = Field(description="Total allocatable CPU")
    allocatable_memory: str = Field(description="Total allocatable memory")
    nodes: list[NodeInfo] = Field(description="Individual node details")


class NamespaceSummary(BaseModel):
    """Summary of resources in a namespace."""

    name: str = Field(description="Namespace name")
    pod_count: int = Field(description="Number of pods")
    running_pods: int = Field(description="Number of running pods")
    deployment_count: int = Field(description="Number of deployments")
    service_count: int = Field(description="Number of services")
    configmap_count: int = Field(description="Number of configmaps")
    secret_count: int = Field(description="Number of secrets")
    total_restarts: int = Field(
        default=0, description="Total container restarts in namespace"
    )
    health_score: float = Field(
        default=1.0, description="Health score 0-1 based on pod status and restarts"
    )
    labels: dict[str, str] = Field(default_factory=dict, description="Namespace labels")


class DeploymentHistoryEntry(BaseModel):
    """A single entry in deployment history (rollout)."""

    revision: int = Field(description="Revision number")
    image: str = Field(description="Container image at this revision")
    created_at: datetime = Field(description="When this revision was created")
    replicas: int = Field(description="Replica count at this revision")
    change_cause: str | None = Field(
        default=None, description="Annotation describing the change"
    )


class RestartPattern(BaseModel):
    """Analyzed restart pattern for a deployment/pod."""

    total_restarts: int = Field(description="Total restart count in period")
    restart_rate_per_hour: float = Field(description="Average restarts per hour")
    crash_reasons: dict[str, int] = Field(
        default_factory=dict,
        description="Crash reasons and their counts (e.g., OOMKilled: 3)",
    )
    restart_times: list[datetime] = Field(
        default_factory=list, description="Timestamps of recent restarts"
    )
    pattern_detected: str | None = Field(
        default=None,
        description="Detected pattern (e.g., 'periodic', 'escalating', 'random')",
    )
    affected_pods: list[str] = Field(
        default_factory=list, description="Pod names that experienced restarts"
    )
