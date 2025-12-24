"""Tests for retry logic with exponential backoff."""
import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

from agent_observable_core.retry import (  # type: ignore
    retry_with_backoff,
    retry_with_backoff_decorator,
    RetryConfig,
)


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Function succeeds on first attempt."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(test_func)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Function succeeds after retries."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        config = RetryConfig.create(max_attempts=3, initial_delay=0.01)
        result = await retry_with_backoff(test_func, config=config)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_attempts(self):
        """Function raises exception after all retries exhausted."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        config = RetryConfig.create(max_attempts=3, initial_delay=0.01)
        with pytest.raises(ValueError, match="Persistent error"):
            await retry_with_backoff(test_func, config=config)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """Verify exponential backoff timing."""
        sleep_times = []
        call_count = 0

        # Mock asyncio.sleep to capture delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            sleep_times.append(delay)
            await original_sleep(0.01)  # Minimal actual sleep for test speed

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Error")
            return "success"

        config = RetryConfig.create(
            max_attempts=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            jitter=False,  # Disable jitter for predictable timing
        )

        # Temporarily replace asyncio.sleep
        import taskpilot.core.retry as retry_module
        original_retry_sleep = retry_module.asyncio.sleep
        retry_module.asyncio.sleep = mock_sleep

        try:
            await retry_with_backoff(test_func, config=config)
        finally:
            retry_module.asyncio.sleep = original_retry_sleep

        # Should have 2 sleep calls (between attempts 1-2 and 2-3)
        assert len(sleep_times) == 2
        # First delay should be ~0.1s, second should be ~0.2s
        assert 0.09 < sleep_times[0] < 0.11
        assert 0.19 < sleep_times[1] < 0.21

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Verify max_delay caps the delay."""
        delays = []
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                delays.append(time.time())
                raise ValueError("Error")
            return "success"

        config = RetryConfig.create(
            max_attempts=3,
            initial_delay=10.0,  # Start with 10s
            backoff_factor=10.0,  # Multiply by 10
            max_delay=0.5,  # But cap at 0.5s
            jitter=False,
        )

        start_time = time.time()
        await retry_with_backoff(test_func, config=config)
        end_time = time.time()

        # Both delays should be capped at 0.5s
        if len(delays) >= 2:
            delay1 = delays[0] - start_time
            delay2 = delays[1] - delays[0]
            assert delay1 <= 0.6  # Allow some tolerance
            assert delay2 <= 0.6

    @pytest.mark.asyncio
    async def test_retryable_exceptions(self):
        """Only retries on specified exceptions."""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            raise KeyError("Not retryable")

        config = RetryConfig.create(
            max_attempts=3,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,),  # Only retry on ValueError
        )

        with pytest.raises(KeyError):
            await retry_with_backoff(test_func, config=config)
        # Should only call once since KeyError is not retryable
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_metrics_callback(self):
        """Metrics callback is invoked."""
        metrics_calls = []

        def metrics_callback(name: str, value: float):
            metrics_calls.append((name, value))

        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Error")
            return "success"

        config = RetryConfig.create(
            max_attempts=3,
            initial_delay=0.01,
            metrics_callback=metrics_callback,
        )

        await retry_with_backoff(test_func, config=config)

        # Should have retry.attempts call and retry.success_after_attempts
        assert len(metrics_calls) >= 1
        assert any(name == "retry.attempts" for name, _ in metrics_calls)


class TestRetryDecorator:
    """Test retry_with_backoff_decorator."""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Decorator works correctly."""
        call_count = 0

        @retry_with_backoff_decorator(max_attempts=3, initial_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Error")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_exhausts(self):
        """Decorator exhausts attempts correctly."""
        call_count = 0

        @retry_with_backoff_decorator(max_attempts=3, initial_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(ValueError):
            await test_func()
        assert call_count == 3


class TestRetryConfig:
    """Test RetryConfig."""

    def test_create_default(self):
        """Test creating config with defaults."""
        config = RetryConfig.create()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True

    def test_create_custom(self):
        """Test creating config with custom values."""
        config = RetryConfig.create(
            max_attempts=5,
            initial_delay=2.0,
            backoff_factor=3.0,
            max_delay=120.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.backoff_factor == 3.0
        assert config.max_delay == 120.0
        assert config.jitter is False
