"""Retry logic with exponential backoff."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Awaitable, Any, Optional, Tuple, Type, Union

logger = logging.getLogger(__name__)


def create_retry_config_from_app_config(
    metrics_callback: Optional[Callable[[str, float], None]] = None,
) -> RetryConfig:
    """Create RetryConfig from AppConfig.

    Args:
        metrics_callback: Optional metrics callback (if None, will try to get from observability)

    Returns:
        RetryConfig instance
    """
    try:
        from taskpilot.core.config import get_app_config
        app_config = get_app_config()

        # Create metrics callback if not provided
        if metrics_callback is None:
            def default_metrics_callback(name: str, value: float):
                try:
                    from taskpilot.core.observable import get_metrics
                    from taskpilot.core.metric_names import (
                        RETRY_ATTEMPTS,
                        RETRY_SUCCESS_AFTER_ATTEMPTS,
                        RETRY_EXHAUSTED,
                    )
                    metrics = get_metrics()
                    if name == "retry.attempts":
                        metrics.increment_counter(RETRY_ATTEMPTS, value)
                    elif name == "retry.success_after_attempts":
                        metrics.record_histogram(RETRY_SUCCESS_AFTER_ATTEMPTS, value)
                    elif name == "retry.exhausted":
                        metrics.increment_counter(RETRY_EXHAUSTED, value)
                except Exception:
                    pass

            metrics_callback = default_metrics_callback

        return RetryConfig.create(
            max_attempts=app_config.retry_max_attempts,
            initial_delay=app_config.retry_initial_delay,
            backoff_factor=app_config.retry_backoff_factor,
            max_delay=app_config.retry_max_delay,
            metrics_callback=metrics_callback,
        )
    except Exception:
        # Fallback to defaults if config not available
        return RetryConfig.create(metrics_callback=metrics_callback)


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

        Returns:
            RetryConfig instance
        """
        if retryable_exceptions is None:
            retryable_exceptions = (Exception,)

        return cls(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            metrics_callback=metrics_callback,
        )


async def retry_with_backoff(
    func: Callable[..., Awaitable[Any]],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """Execute a function with retry logic and exponential backoff.

    Args:
        func: Async function to execute
        config: Optional retry configuration (uses defaults if not provided)
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        Last exception if all retries are exhausted
    """
    if config is None:
        config = RetryConfig.create()

    delay = config.initial_delay
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            # Track success metric if callback provided
            if config.metrics_callback and attempt > 0:
                try:
                    config.metrics_callback("retry.success_after_attempts", float(attempt + 1))
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
    )

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await retry_with_backoff(func, config, *args, **kwargs)

        return wrapper

    return decorator
