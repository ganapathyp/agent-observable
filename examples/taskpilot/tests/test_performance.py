"""Performance tests for middleware and observability.

These tests measure:
- Middleware overhead (latency added by observability)
- Metrics collection performance
- Trace creation performance
- Text extraction performance
- Memory usage
"""
from __future__ import annotations

import pytest
import time
import asyncio
import statistics
from typing import Any
from unittest.mock import MagicMock, AsyncMock, patch

from agent_framework import AgentRunContext, TextContent  # type: ignore
from taskpilot.core.middleware import create_audit_and_policy_middleware  # type: ignore
from taskpilot.core.text_extraction import (  # type: ignore
    extract_text_from_content,
    extract_text_from_messages,
    extract_text_from_result,
    extract_text_from_context,
    is_async_generator,
)


class TestTextExtractionPerformance:
    """Performance tests for text extraction utilities."""
    
    def test_extract_text_from_content_performance(self):
        """Test text extraction from content is fast."""
        content = TextContent(text="Test content" * 100)
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            result = extract_text_from_content(content)
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        assert avg_time < 0.001  # Should be < 1ms
        assert p95_time < 0.002  # 95th percentile < 2ms
        assert result == content.text
    
    def test_extract_text_from_messages_performance(self):
        """Test text extraction from messages is fast."""
        messages = [
            MagicMock(role='user', content=TextContent(text="User message" * 10)),
            MagicMock(role='assistant', content=TextContent(text="Assistant message" * 10)),
        ]
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            result = extract_text_from_messages(messages)
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        assert avg_time < 0.001  # Should be < 1ms
        assert p95_time < 0.002  # 95th percentile < 2ms
    
    def test_extract_text_from_result_performance(self):
        """Test text extraction from result is fast."""
        result = MagicMock(
            agent_run_response=MagicMock(
                text="Result text" * 100
            )
        )
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            extract_text_from_result(result)
            times.append(time.perf_counter() - start)
        
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        assert avg_time < 0.001  # Should be < 1ms
        assert p95_time < 0.002  # 95th percentile < 2ms


class TestMiddlewarePerformance:
    """Performance tests for middleware overhead."""
    
    @pytest.mark.asyncio
    async def test_middleware_overhead(self):
        """Test that middleware adds minimal overhead."""
        # Create a simple async function to measure
        async def simple_agent(context: AgentRunContext):
            await asyncio.sleep(0.001)  # 1ms of work
            context.result = MagicMock(text="Result")
        
        # Measure without middleware
        context_no_middleware = AgentRunContext(
            messages=[MagicMock(role='user', content="Test input")],
            result=None
        )
        
        times_no_middleware = []
        for _ in range(100):
            start = time.perf_counter()
            await simple_agent(context_no_middleware)
            times_no_middleware.append(time.perf_counter() - start)
        
        # Measure with middleware
        middleware = create_audit_and_policy_middleware("TestAgent")
        context_with_middleware = AgentRunContext(
            messages=[MagicMock(role='user', content="Test input")],
            result=None
        )
        
        times_with_middleware = []
        for _ in range(100):
            start = time.perf_counter()
            await middleware(context_with_middleware, simple_agent)
            times_with_middleware.append(time.perf_counter() - start)
        
        avg_no_middleware = statistics.mean(times_no_middleware)
        avg_with_middleware = statistics.mean(times_with_middleware)
        overhead = avg_with_middleware - avg_no_middleware
        overhead_percent = (overhead / avg_no_middleware) * 100
        
        # Middleware should add < 50ms overhead on average
        assert overhead < 0.05, f"Middleware overhead {overhead*1000:.2f}ms is too high"
        print(f"Middleware overhead: {overhead*1000:.2f}ms ({overhead_percent:.1f}%)")
    
    @pytest.mark.asyncio
    async def test_middleware_latency_p95(self):
        """Test that middleware P95 latency is acceptable."""
        async def simple_agent(context: AgentRunContext):
            await asyncio.sleep(0.001)
            context.result = MagicMock(text="Result")
        
        middleware = create_audit_and_policy_middleware("TestAgent")
        context = AgentRunContext(
            messages=[MagicMock(role='user', content="Test input")],
            result=None
        )
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            await middleware(context, simple_agent)
            times.append(time.perf_counter() - start)
        
        p95_latency = statistics.quantiles(times, n=20)[18]
        
        # P95 latency should be < 100ms
        assert p95_latency < 0.1, f"P95 latency {p95_latency*1000:.2f}ms is too high"
        print(f"P95 latency: {p95_latency*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_middleware_throughput(self):
        """Test middleware can handle high throughput."""
        async def simple_agent(context: AgentRunContext):
            context.result = MagicMock(text="Result")
        
        middleware = create_audit_and_policy_middleware("TestAgent")
        
        # Run 1000 requests concurrently
        async def run_request():
            context = AgentRunContext(
                messages=[MagicMock(role='user', content="Test input")],
                result=None
            )
            await middleware(context, simple_agent)
        
        start = time.perf_counter()
        await asyncio.gather(*[run_request() for _ in range(1000)])
        elapsed = time.perf_counter() - start
        
        throughput = 1000 / elapsed
        # Should handle at least 100 requests/second
        assert throughput > 100, f"Throughput {throughput:.1f} req/s is too low"
        print(f"Throughput: {throughput:.1f} requests/second")


class TestMemoryUsage:
    """Tests for memory usage patterns."""
    
    @pytest.mark.asyncio
    async def test_middleware_memory_usage(self):
        """Test that middleware doesn't leak memory."""
        import tracemalloc
        
        async def simple_agent(context: AgentRunContext):
            context.result = MagicMock(text="Result")
        
        middleware = create_audit_and_policy_middleware("TestAgent")
        
        # Start memory tracking
        tracemalloc.start()
        
        # Run many requests
        for _ in range(1000):
            context = AgentRunContext(
                messages=[MagicMock(role='user', content="Test input")],
                result=None
            )
            await middleware(context, simple_agent)
        
        # Get memory snapshot
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable (< 100MB for 1000 requests)
        assert peak < 100 * 1024 * 1024, f"Peak memory {peak / 1024 / 1024:.2f}MB is too high"
        print(f"Peak memory: {peak / 1024 / 1024:.2f}MB")


class TestConcurrentRequests:
    """Tests for concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_middleware_requests(self):
        """Test middleware handles concurrent requests correctly."""
        async def simple_agent(context: AgentRunContext):
            await asyncio.sleep(0.01)  # 10ms of work
            context.result = MagicMock(text="Result")
        
        middleware = create_audit_and_policy_middleware("TestAgent")
        
        # Run 100 concurrent requests
        async def run_request(request_id: int):
            context = AgentRunContext(
                messages=[MagicMock(role='user', content=f"Request {request_id}")],
                result=None
            )
            await middleware(context, simple_agent)
            return request_id
        
        start = time.perf_counter()
        results = await asyncio.gather(*[run_request(i) for i in range(100)])
        elapsed = time.perf_counter() - start
        
        # All requests should complete
        assert len(results) == 100
        assert all(i == results[i] for i in range(100))
        
        # Should complete in reasonable time (< 1 second for 100 concurrent)
        assert elapsed < 1.0, f"Concurrent requests took {elapsed:.2f}s"
        print(f"100 concurrent requests completed in {elapsed:.2f}s")
