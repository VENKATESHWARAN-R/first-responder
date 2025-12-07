"""
Observer MCP - Kubernetes Cluster Observability Tooling

A comprehensive Python tooling library for AI-powered Kubernetes observability.
Provides structured data access to Kubernetes resources and Prometheus metrics.
"""

from observer_mcp.config import Settings
from observer_mcp.models.responses import ToolResponse, ToolStatus

__version__ = "0.1.0"
__all__ = ["ToolResponse", "ToolStatus", "Settings"]
