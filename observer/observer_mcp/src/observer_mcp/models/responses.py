"""
Standard response models for all tools.

All tools return a ToolResponse with consistent structure for AI consumption.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """
    Status of tool execution.

    Attributes:
        SUCCESS: Tool completed successfully with all data retrieved.
        PARTIAL: Tool completed but some data may be missing or truncated.
        ERROR: Tool failed to complete the requested operation.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class ToolResponse(BaseModel):
    """
    Standardized response format for all observability tools.

    This consistent structure helps the AI agent understand tool outcomes
    without parsing different response formats for each tool.

    Attributes:
        status: Execution status (success, partial, or error).
        result: The actual data returned by the tool. Type varies by tool.
        error: Error message if status is ERROR, otherwise None.
        warnings: List of non-fatal issues encountered during execution.
        metadata: Execution metadata like timing, counts, and query details.

    Example:
        ```python
        {
            "status": "success",
            "result": {"deployments": [...]},
            "error": null,
            "warnings": [],
            "metadata": {
                "execution_time_ms": 45,
                "namespace": "load-tester",
                "timestamp": "2025-12-08T00:00:00Z"
            }
        }
        ```
    """

    status: ToolStatus = Field(
        description="Execution status: success, partial, or error"
    )
    result: Any = Field(
        default=None, description="The actual data returned by the tool"
    )
    error: str | None = Field(
        default=None, description="Error message if status is error"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues encountered during execution",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (timing, counts, query parameters)",
    )

    @classmethod
    def success(
        cls,
        result: Any,
        metadata: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> "ToolResponse":
        """
        Create a successful response.

        Args:
            result: The data to return.
            metadata: Optional execution metadata.
            warnings: Optional list of warnings.

        Returns:
            ToolResponse with SUCCESS status.
        """
        return cls(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata=metadata or {},
            warnings=warnings or [],
        )

    @classmethod
    def partial(
        cls,
        result: Any,
        warnings: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResponse":
        """
        Create a partial success response.

        Use when some data was retrieved but there were issues.

        Args:
            result: The partial data retrieved.
            warnings: List of issues encountered.
            metadata: Optional execution metadata.

        Returns:
            ToolResponse with PARTIAL status.
        """
        return cls(
            status=ToolStatus.PARTIAL,
            result=result,
            warnings=warnings,
            metadata=metadata or {},
        )

    @classmethod
    def error(
        cls,
        error_message: str,
        error_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResponse":
        """
        Create an error response.

        Args:
            error_message: Human-readable error description.
            error_type: Optional error class name for categorization.
            metadata: Optional execution metadata.

        Returns:
            ToolResponse with ERROR status.
        """
        meta = metadata or {}
        if error_type:
            meta["error_type"] = error_type
        return cls(
            status=ToolStatus.ERROR,
            result=None,
            error=error_message,
            metadata=meta,
        )


def add_execution_metadata(
    metadata: dict[str, Any],
    start_time: datetime,
    **extra: Any,
) -> dict[str, Any]:
    """
    Add standard execution metadata to a response.

    Args:
        metadata: Existing metadata dict to extend.
        start_time: When the tool execution started.
        **extra: Additional metadata key-value pairs.

    Returns:
        Extended metadata dict with timing info.
    """
    end_time = datetime.now()
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

    return {
        **metadata,
        "execution_time_ms": execution_time_ms,
        "timestamp": end_time.isoformat(),
        **extra,
    }
