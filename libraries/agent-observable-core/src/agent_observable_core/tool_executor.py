"""Tool execution utilities with timeout and error handling (framework-agnostic).

Automatically tracks tool metrics using standardized metric names.
Works across all frameworks: MS Agent Framework, LangGraph, OpenAI routing.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Awaitable, Any, Optional, Dict

from agent_observable_core.exceptions import ToolTimeoutError, ToolExecutionError
from agent_observable_core.framework_detector import get_metric_standardizer

logger = logging.getLogger(__name__)


async def execute_tool_with_timeout(
    tool_func: Callable[..., Awaitable[Any]],
    tool_name: str,
    timeout_seconds: Optional[float] = None,
    metrics_collector: Optional[Any] = None,
    service_name: str = "agent-service",
    *args,
    **kwargs
) -> Any:
    """Execute a tool function with timeout protection.

    Automatically tracks tool metrics using standardized metric names.

    Args:
        tool_func: Async tool function to execute
        tool_name: Name of the tool (for error messages and metrics)
        timeout_seconds: Timeout in seconds (defaults to 30.0)
        metrics_collector: Optional MetricsCollector instance for tracking metrics
        service_name: Service name for metric standardization
        *args: Positional arguments for tool function
        **kwargs: Keyword arguments for tool function

    Returns:
        Tool execution result

    Raises:
        ToolTimeoutError: If tool execution exceeds timeout
        ToolExecutionError: If tool execution fails
    """
    if timeout_seconds is None:
        timeout_seconds = 30.0  # Default timeout

    # Get metric standardizer for standardized metric names
    standardizer = get_metric_standardizer(service_name=service_name)

    start_time = time.time()

    try:
        # Execute tool with timeout
        result = await asyncio.wait_for(
            tool_func(*args, **kwargs),
            timeout=timeout_seconds
        )

        execution_time = time.time() - start_time
        logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")

        # Track success metrics
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_calls(tool_name))
                metrics_collector.increment_counter(standardizer.tool_success(tool_name))
                metrics_collector.record_histogram(
                    standardizer.tool_latency_ms(tool_name),
                    execution_time * 1000  # Convert to milliseconds
                )
            except Exception:
                pass

        return result

    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} timed out after {execution_time:.2f}s (limit: {timeout_seconds}s)")

        # Track timeout metric
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_errors(tool_name))
            except Exception:
                pass

        raise ToolTimeoutError(
            tool_name=tool_name,
            timeout_seconds=timeout_seconds,
            details={"execution_time": execution_time}
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} execution failed after {execution_time:.2f}s: {e}", exc_info=True)

        # Track error metric
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_errors(tool_name))
            except Exception:
                pass

        # If it's already a ToolException, re-raise it
        if isinstance(e, (ToolTimeoutError, ToolExecutionError)):
            raise

        # Otherwise, wrap it in ToolExecutionError
        raise ToolExecutionError(
            tool_name=tool_name,
            reason=str(e),
            details={"execution_time": execution_time, "original_error": type(e).__name__}
        )


def execute_tool_sync_with_timeout(
    tool_func: Callable[..., Any],
    tool_name: str,
    timeout_seconds: Optional[float] = None,
    metrics_collector: Optional[Any] = None,
    service_name: str = "agent-service",
    *args,
    **kwargs
) -> Any:
    """Execute a synchronous tool function with timeout protection.

    This is a wrapper for sync tools that need timeout protection.
    It runs the sync function in a thread pool executor.

    Args:
        tool_func: Synchronous tool function to execute
        tool_name: Name of the tool (for error messages and metrics)
        timeout_seconds: Timeout in seconds (defaults to 30.0)
        metrics_collector: Optional MetricsCollector instance for tracking metrics
        service_name: Service name for metric standardization
        *args: Positional arguments for tool function
        **kwargs: Keyword arguments for tool function

    Returns:
        Tool execution result

    Raises:
        ToolTimeoutError: If tool execution exceeds timeout
        ToolExecutionError: If tool execution fails
    """
    import concurrent.futures

    if timeout_seconds is None:
        timeout_seconds = 30.0  # Default timeout

    # Get metric standardizer for standardized metric names
    standardizer = get_metric_standardizer(service_name=service_name)

    start_time = time.time()

    try:
        # Run sync function in thread pool with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool_func, *args, **kwargs)
            result = future.result(timeout=timeout_seconds)

        execution_time = time.time() - start_time
        logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")

        # Track success metrics
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_calls(tool_name))
                metrics_collector.increment_counter(standardizer.tool_success(tool_name))
                metrics_collector.record_histogram(
                    standardizer.tool_latency_ms(tool_name),
                    execution_time * 1000  # Convert to milliseconds
                )
            except Exception:
                pass

        return result

    except concurrent.futures.TimeoutError:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} timed out after {execution_time:.2f}s (limit: {timeout_seconds}s)")

        # Track timeout metric
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_errors(tool_name))
            except Exception:
                pass

        raise ToolTimeoutError(
            tool_name=tool_name,
            timeout_seconds=timeout_seconds,
            details={"execution_time": execution_time}
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} execution failed after {execution_time:.2f}s: {e}", exc_info=True)

        # Track error metric
        if metrics_collector:
            try:
                metrics_collector.increment_counter(standardizer.tool_errors(tool_name))
            except Exception:
                pass

        if isinstance(e, (ToolTimeoutError, ToolExecutionError)):
            raise

        raise ToolExecutionError(
            tool_name=tool_name,
            reason=str(e),
            details={"execution_time": execution_time, "original_error": type(e).__name__}
        )


__all__ = [
    "execute_tool_with_timeout",
    "execute_tool_sync_with_timeout",
]
