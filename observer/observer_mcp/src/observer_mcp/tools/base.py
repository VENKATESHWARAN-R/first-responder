"""
Base utilities for tool implementations.

Provides decorators and helpers for consistent tool behavior.
"""

from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

from observer_mcp.clients.kubernetes import K8sClientError, K8sNotFoundError
from observer_mcp.clients.prometheus import PrometheusClientError, PrometheusQueryError
from observer_mcp.models.responses import ToolResponse, add_execution_metadata

F = TypeVar("F", bound=Callable[..., ToolResponse])


def tool_handler(func: F) -> F:
    """
    Decorator for tool functions that provides:
    - Automatic exception handling
    - Execution timing
    - Consistent error responses

    Args:
        func: Tool function to wrap.

    Returns:
        Wrapped function with error handling.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ToolResponse:
        start_time = datetime.now()

        try:
            result = func(*args, **kwargs)

            # Add execution time to metadata if not already present
            if "execution_time_ms" not in result.metadata:
                result.metadata = add_execution_metadata(
                    result.metadata,
                    start_time,
                )
            return result

        except K8sNotFoundError as e:
            return ToolResponse.error(
                error_message=str(e),
                error_type="NotFoundError",
                metadata=add_execution_metadata({}, start_time),
            )
        except K8sClientError as e:
            return ToolResponse.error(
                error_message=str(e),
                error_type="KubernetesError",
                metadata=add_execution_metadata({}, start_time),
            )
        except PrometheusQueryError as e:
            return ToolResponse.error(
                error_message=str(e),
                error_type="PrometheusQueryError",
                metadata=add_execution_metadata({}, start_time),
            )
        except PrometheusClientError as e:
            return ToolResponse.error(
                error_message=str(e),
                error_type="PrometheusError",
                metadata=add_execution_metadata({}, start_time),
            )
        except Exception as e:
            return ToolResponse.error(
                error_message=f"Unexpected error: {e}",
                error_type=type(e).__name__,
                metadata=add_execution_metadata({}, start_time),
            )

    return wrapper  # type: ignore


def truncate_logs(logs: str, max_lines: int) -> tuple[str, bool]:
    """
    Truncate logs to a maximum number of lines.

    Args:
        logs: Log content.
        max_lines: Maximum number of lines to keep.

    Returns:
        Tuple of (truncated_logs, was_truncated).
    """
    lines = logs.split("\n")
    if len(lines) <= max_lines:
        return logs, False

    truncated = lines[-max_lines:]
    return "\n".join(truncated), True


def parse_duration(duration: str) -> int:
    """
    Parse a duration string to seconds.

    Args:
        duration: Duration string (e.g., '1h', '24h', '7d', '30d').

    Returns:
        Duration in seconds.

    Raises:
        ValueError: If duration format is invalid.
    """
    duration = duration.strip().lower()

    if duration.endswith("s"):
        return int(duration[:-1])
    elif duration.endswith("m"):
        return int(duration[:-1]) * 60
    elif duration.endswith("h"):
        return int(duration[:-1]) * 3600
    elif duration.endswith("d"):
        return int(duration[:-1]) * 86400
    else:
        raise ValueError(
            f"Invalid duration format: {duration}. Use 's', 'm', 'h', or 'd' suffix."
        )


def format_bytes(bytes_value: int | float) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_value) < 1024:
            return f"{bytes_value:.2f}{unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f}PB"


def format_cpu(cores: float) -> str:
    """Format CPU cores to human-readable string."""
    if cores < 0.001:
        return f"{cores * 1000000:.0f}n"  # nanocores
    elif cores < 1:
        return f"{cores * 1000:.0f}m"  # millicores
    return f"{cores:.2f}"
