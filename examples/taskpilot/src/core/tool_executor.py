"""Tool execution utilities with timeout and error handling."""
import asyncio
import logging
import time
from typing import Callable, Awaitable, Any, Optional, Dict
from taskpilot.core.exceptions import ToolTimeoutError, ToolExecutionError  # type: ignore
from taskpilot.core.config import get_app_config  # type: ignore

logger = logging.getLogger(__name__)


async def execute_tool_with_timeout(
    tool_func: Callable[..., Awaitable[Any]],
    tool_name: str,
    timeout_seconds: Optional[float] = None,
    *args,
    **kwargs
) -> Any:
    """Execute a tool function with timeout protection.
    
    Args:
        tool_func: Async tool function to execute
        tool_name: Name of the tool (for error messages)
        timeout_seconds: Timeout in seconds (defaults to config value)
        *args: Positional arguments for tool function
        **kwargs: Keyword arguments for tool function
        
    Returns:
        Tool execution result
        
    Raises:
        ToolTimeoutError: If tool execution exceeds timeout
        ToolExecutionError: If tool execution fails
    """
    # Get timeout from config if not provided
    if timeout_seconds is None:
        try:
            app_config = get_app_config()
            timeout_seconds = app_config.tool_timeout_seconds
        except Exception:
            # Fallback if config not available
            timeout_seconds = 30.0
    
    start_time = time.time()
    
    try:
        # Execute tool with timeout
        result = await asyncio.wait_for(
            tool_func(*args, **kwargs),
            timeout=timeout_seconds
        )
        
        execution_time = time.time() - start_time
        logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
        
        return result
        
    except asyncio.TimeoutError:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} timed out after {execution_time:.2f}s (limit: {timeout_seconds}s)")
        
        # Track timeout metric
        try:
            from taskpilot.core.observability import get_metrics_collector
            from taskpilot.core.metric_names import OBSERVABILITY_TRACE_EXPORT_FAILURES  # Reuse for now
            metrics = get_metrics_collector()
            # We could add a specific tool timeout counter here
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
    *args,
    **kwargs
) -> Any:
    """Execute a synchronous tool function with timeout protection.
    
    This is a wrapper for sync tools that need timeout protection.
    It runs the sync function in a thread pool executor.
    
    Args:
        tool_func: Synchronous tool function to execute
        tool_name: Name of the tool (for error messages)
        timeout_seconds: Timeout in seconds (defaults to config value)
        *args: Positional arguments for tool function
        **kwargs: Keyword arguments for tool function
        
    Returns:
        Tool execution result
        
    Raises:
        ToolTimeoutError: If tool execution exceeds timeout
        ToolExecutionError: If tool execution fails
    """
    import concurrent.futures
    
    # Get timeout from config if not provided
    if timeout_seconds is None:
        try:
            app_config = get_app_config()
            timeout_seconds = app_config.tool_timeout_seconds
        except Exception:
            timeout_seconds = 30.0
    
    start_time = time.time()
    
    try:
        # Run sync function in thread pool with timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool_func, *args, **kwargs)
            result = future.result(timeout=timeout_seconds)
        
        execution_time = time.time() - start_time
        logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
        
        return result
        
    except concurrent.futures.TimeoutError:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} timed out after {execution_time:.2f}s (limit: {timeout_seconds}s)")
        
        raise ToolTimeoutError(
            tool_name=tool_name,
            timeout_seconds=timeout_seconds,
            details={"execution_time": execution_time}
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} execution failed after {execution_time:.2f}s: {e}", exc_info=True)
        
        if isinstance(e, (ToolTimeoutError, ToolExecutionError)):
            raise
        
        raise ToolExecutionError(
            tool_name=tool_name,
            reason=str(e),
            details={"execution_time": execution_time, "original_error": type(e).__name__}
        )
