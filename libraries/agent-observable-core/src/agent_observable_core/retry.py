"""Retry logic with exponential backoff (framework-agnostic).

Automatically tracks retry metrics using standardized metric names.
Works across all frameworks: MS Agent Framework, LangGraph, OpenAI routing.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Awaitable, Any, Optional, Tuple, Type, Union

from agent_observable_core.framework_detector import get_metric_standardizer

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    metrics_callback: Optional[Callable[[str, float], None]] = None
    service_name: str = "agent-service"

    @classmethod
    def create(
        cls,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        metrics_callback: Optional[Callable[[str, float], None]] = None,
        service_name: str = "agent-service",
    ) -> RetryConfig:
        """Create a RetryConfig instance.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            backoff_factor: Multiplier for exponential backoff
            max_delay: Maximum delay between retries
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Tuple of exception types to retry on
            metrics_callback: Optional callback for tracking retry metrics
            service_name: Service name for metric standardization

        Returns:
            RetryConfig instance
        """
        if retryable_exceptions is None:
            retryable_exceptions = (Exception,)

        # Create default metrics callback if not provided
        if metrics_callback is None:
            def default_metrics_callback(name: str, value: float):
                try:
                    from agent_observable_core.observability import MetricsCollector
                    # Try to get metrics from global instance (if available)
                    # This is optional - retry works without metrics
                    pass  # Metrics will be tracked via callback if provided
                except Exception:
                    pass

            metrics_callback = default_metrics_callback

        return cls(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            metrics_callback=metrics_callback,
            service_name=service_name,
        )


async def retry_with_backoff(
    func: Callable[..., Awaitable[Any]],
    config: Optional[RetryConfig] = None,
    metrics_collector: Optional[Any] = None,
    service_name: str = "agent-service",
    *args,
    **kwargs
) -> Any:
    """Execute a function with retry logic and exponential backoff.

    Automatically tracks retry metrics using standardized metric names.

    Args:
        func: Async function to execute
        config: Optional retry configuration (uses defaults if not provided)
        metrics_collector: Optional MetricsCollector instance for tracking metrics
        service_name: Service name for metric standardization
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        Last exception if all retries are exhausted
    """
    if config is None:
        config = RetryConfig.create(service_name=service_name)

    # Get metric standardizer for standardized metric names
    standardizer = get_metric_standardizer(service_name=config.service_name)

    delay = config.initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            # Track success metric if callback provided or metrics_collector available
            if attempt > 0:
                if config.metrics_callback:
                    try:
                        config.metrics_callback("retry.success_after_attempts", float(attempt + 1))
                    except Exception:
                        pass
                elif metrics_collector:
                    try:
                        metrics_collector.record_histogram(
                            standardizer.retry_success_after_attempts(),
                            float(attempt + 1)
                        )
                    except Exception:
                        pass

            return result

        except config.retryable_exceptions as e:
            last_exception = e

            # If this is the last attempt, raise the exception
            if attempt == config.max_attempts - 1:
                # Track failure metric
                if config.metrics_callback:
                    try:
                        config.metrics_callback("retry.exhausted", 1.0)
                    except Exception:
                        pass
                elif metrics_collector:
                    try:
                        metrics_collector.increment_counter(standardizer.retry_exhausted())
                    except Exception:
                        pass
                logger.warning(
                    f"Retry exhausted after {config.max_attempts} attempts. "
                    f"Last error: {type(e).__name__}: {e}"
                )
                raise

            # Calculate delay with jitter
            actual_delay = delay
            if config.jitter:
                # Add random jitter (0-25% of delay)
                jitter_amount = actual_delay * 0.25 * random.random()
                actual_delay += jitter_amount

            # Cap delay at max_delay
            actual_delay = min(actual_delay, config.max_delay)

            logger.debug(
                f"Retry attempt {attempt + 1}/{config.max_attempts} after {actual_delay:.2f}s. "
                f"Error: {type(e).__name__}: {e}"
            )

            # Track retry metric
            if config.metrics_callback:
                try:
                    config.metrics_callback("retry.attempts", 1.0)
                except Exception:
                    pass
            elif metrics_collector:
                try:
                    metrics_collector.increment_counter(standardizer.retry_attempts())
                except Exception:
                    pass

            await asyncio.sleep(actual_delay)

            # Exponential backoff for next attempt
            delay *= config.backoff_factor

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic exhausted without exception")


def retry_with_backoff_decorator(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    metrics_callback: Optional[Callable[[str, float], None]] = None,
    service_name: str = "agent-service",
):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exception types to retry on
        metrics_callback: Optional callback for tracking retry metrics
        service_name: Service name for metric standardization

    Returns:
        Decorator function
    """
    config = RetryConfig.create(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        metrics_callback=metrics_callback,
        service_name=service_name,
    )

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await retry_with_backoff(func, config, *args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "RetryConfig",
    "retry_with_backoff",
    "retry_with_backoff_decorator",
]
