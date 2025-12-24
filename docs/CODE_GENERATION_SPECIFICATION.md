# Code Generation Specification

**Purpose:** This specification enables LLM-driven code generation for `agent-observable-core` library and extensions. Use this document to train LLMs or guide developers to generate code that follows the same patterns, architecture, and standards.

**Version:** 1.0  
**Last Updated:** 2025-12-24

**Usage:** Provide this specification to an LLM along with a feature request to generate code that matches the existing codebase patterns.

---

## Table of Contents

1. [Architecture Principles](#architecture-principles)
2. [Code Patterns](#code-patterns)
3. [Module Structure](#module-structure)
4. [API Contracts](#api-contracts)
5. [Error Handling](#error-handling)
6. [Type Annotations](#type-annotations)
7. [Testing Requirements](#testing-requirements)
8. [Documentation Standards](#documentation-standards)
9. [Framework-Agnostic Design](#framework-agnostic-design)
10. [Example Specifications](#example-specifications)

---

## Architecture Principles

### 1. Framework-Agnostic Design

**Principle:** All code must work with multiple agent frameworks (MS Agent Framework, LangGraph, OpenAI custom routing) without framework-specific dependencies.

**Rules:**
- Use abstract interfaces, not concrete framework types
- Detect framework at runtime, don't hardcode assumptions
- Provide framework-agnostic abstractions (hooks, callbacks)
- Never import framework-specific modules in core code

**Example:**
```python
# ✅ GOOD: Framework-agnostic
def extract_text_from_response(response: Any) -> Optional[str]:
    """Extract text from any framework's response."""
    # Try multiple patterns
    if hasattr(response, 'text'):
        return response.text
    if hasattr(response, 'content'):
        return response.content
    if isinstance(response, str):
        return response
    return None

# ❌ BAD: Framework-specific
from agent_framework import AgentResponse
def extract_text(response: AgentResponse) -> str:
    return response.text
```

### 2. Declarative Configuration

**Principle:** Use dataclasses and configuration objects instead of global state or environment variables.

**Rules:**
- All configuration via dataclasses (`@dataclass`)
- Default values in dataclass fields
- Optional dependency injection via constructor
- No global configuration state

**Example:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ObservabilityConfig:
    """Configuration for observability components."""
    metrics_max_samples: int = 1000
    error_tracker_max_errors: int = 1000
    tracer_max_spans: int = 1000
    
    def create_metrics_collector(self) -> "MetricsCollector":
        """Create a MetricsCollector with this configuration."""
        return MetricsCollector(max_samples=self.metrics_max_samples)
```

### 3. Zero-Configuration Defaults

**Principle:** Everything should work out-of-the-box with sensible defaults.

**Rules:**
- All optional parameters have defaults
- No required configuration for basic usage
- Sensible defaults for all settings
- Progressive enhancement (basic → advanced)

**Example:**
```python
def create_observable_middleware(
    service_name: str = "agent-service",
    enable_metrics: bool = True,
    enable_tracing: bool = True,
    enable_policy: bool = True,
    enable_guardrails: bool = True,
    enable_cost_tracking: bool = True,
    # ... all optional with defaults
) -> Callable:
    """Create middleware with zero configuration required."""
    pass
```

### 4. Automatic Instrumentation

**Principle:** Observability should be automatic, not manual.

**Rules:**
- Middleware automatically wraps agent/tool calls
- Metrics automatically recorded
- Traces automatically created
- No manual instrumentation needed
- Use decorators or middleware patterns

**Example:**
```python
# ✅ GOOD: Automatic via middleware
middleware = create_observable_middleware(service_name="my-service")
# Everything is automatically tracked

# ❌ BAD: Manual instrumentation
def my_agent():
    metrics.increment("agent.calls")  # Manual
    trace.start_span("agent")  # Manual
    # ...
```

### 5. Standardized Naming

**Principle:** Use consistent naming patterns across all metrics, traces, and logs.

**Rules:**
- Metrics: `{category}.{entity}.{metric}` (e.g., `workflow.runs`, `agent.{name}.invocations`)
- Traces: `{service}.{type}.{name}` (e.g., `taskpilot.workflow.run`, `taskpilot.agent.PlannerAgent.run`)
- Use `MetricNameStandardizer` and `TraceNameStandardizer` classes
- Never hardcode metric/trace names

**Example:**
```python
# ✅ GOOD: Standardized
standardizer = get_metric_standardizer(service_name="my-service")
metric_name = standardizer.agent_invocations("PlannerAgent")
# Returns: "agent.PlannerAgent.invocations"

# ❌ BAD: Hardcoded
metric_name = "my_service_planner_agent_calls"  # Inconsistent
```

---

## Code Patterns

### 1. Module Structure

**Pattern:**
```python
"""Module docstring describing purpose and framework-agnostic nature."""
from __future__ import annotations

import logging
from typing import Optional, Any, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 1. Type definitions (if any)
# 2. Configuration dataclasses
# 3. Exception classes (if module-specific)
# 4. Core classes
# 5. Helper functions
# 6. Public API exports

__all__ = ["PublicClass", "public_function"]
```

### 2. Class Definition Pattern

**Pattern:**
```python
class MyClass:
    """Class docstring with purpose and usage.
    
    This class does X, Y, Z in a framework-agnostic way.
    
    Example:
        >>> instance = MyClass(config=MyConfig())
        >>> result = instance.do_something()
    """
    
    def __init__(
        self,
        config: Optional[MyConfig] = None,
        dependency: Optional[Dependency] = None,
    ) -> None:
        """Initialize with optional configuration.
        
        Args:
            config: Optional configuration (uses defaults if None)
            dependency: Optional dependency injection
        """
        self._config = config or MyConfig()
        self._dependency = dependency or DefaultDependency()
        self._lock = threading.Lock()  # If thread-safe needed
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    def public_method(self, param: str) -> Optional[Any]:
        """Public method with docstring.
        
        Args:
            param: Parameter description
            
        Returns:
            Return value description, None if not available
            
        Raises:
            SpecificException: When specific error occurs
        """
        with self._lock:  # If thread-safe
            try:
                # Implementation
                return result
            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__}.{method_name}: {e}", exc_info=True)
                raise
```

### 3. Async Function Pattern

**Pattern:**
```python
async def async_function(
    param: str,
    timeout: float = 30.0,
    metrics_collector: Optional[MetricsCollector] = None,
) -> Optional[Any]:
    """Async function with timeout and metrics.
    
    Args:
        param: Parameter description
        timeout: Timeout in seconds (default: 30.0)
        metrics_collector: Optional metrics collector for tracking
        
    Returns:
        Result or None if timeout/error
        
    Raises:
        TimeoutError: If operation exceeds timeout
        SpecificError: For specific error cases
    """
    start_time = time.time()
    
    try:
        # Use asyncio.wait_for for timeout
        result = await asyncio.wait_for(
            _internal_async_operation(param),
            timeout=timeout
        )
        
        # Track metrics if available
        if metrics_collector:
            latency_ms = (time.time() - start_time) * 1000
            metrics_collector.record_histogram("operation.latency_ms", latency_ms)
            metrics_collector.increment_counter("operation.success")
        
        return result
        
    except asyncio.TimeoutError:
        if metrics_collector:
            metrics_collector.increment_counter("operation.timeout")
        logger.warning(f"Operation timed out after {timeout}s")
        raise TimeoutError(f"Operation exceeded {timeout}s timeout")
    except Exception as e:
        if metrics_collector:
            metrics_collector.increment_counter("operation.errors")
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

### 4. Decorator Pattern

**Pattern:**
```python
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

def observable_decorator(
    metric_name: Optional[str] = None,
    trace_name: Optional[str] = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator that adds observability to functions.
    
    Args:
        metric_name: Optional metric name to track
        trace_name: Optional trace name
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Pre-execution: start trace, record start metric
            request_id = get_request_id() or generate_request_id()
            trace_context = None
            
            if trace_name:
                trace_context = TraceContext(name=trace_name, request_id=request_id)
                trace_context.__enter__()
            
            start_time = time.time()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Post-execution: record success metrics
                latency_ms = (time.time() - start_time) * 1000
                if metric_name:
                    metrics_collector.increment_counter(f"{metric_name}.success")
                    metrics_collector.record_histogram(f"{metric_name}.latency_ms", latency_ms)
                
                return result
                
            except Exception as e:
                # Error handling: record error metrics
                if metric_name:
                    metrics_collector.increment_counter(f"{metric_name}.errors")
                
                # Add error to trace
                if trace_context:
                    trace_context.span.tags["error"] = "true"
                    trace_context.span.tags["error.message"] = str(e)
                
                raise
            finally:
                # Cleanup: end trace
                if trace_context:
                    trace_context.__exit__(None, None, None)
        
        return wrapper
    return decorator
```

### 5. Context Manager Pattern

**Pattern:**
```python
class MyContext:
    """Context manager for resource management.
    
    Example:
        >>> with MyContext(config) as ctx:
        ...     ctx.do_work()
    """
    
    def __init__(self, config: MyConfig) -> None:
        """Initialize context."""
        self._config = config
        self._resource: Optional[Resource] = None
    
    def __enter__(self) -> "MyContext":
        """Enter context, acquire resources."""
        self._resource = acquire_resource(self._config)
        logger.debug("Entered context")
        return self
    
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Exit context, release resources.
        
        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value
            exc_tb: Traceback
            
        Returns:
            True to suppress exception, False to propagate
        """
        if self._resource:
            release_resource(self._resource)
            self._resource = None
        logger.debug("Exited context")
        return False  # Don't suppress exceptions
```

---

## Module Structure

### Standard Module Layout

```
src/agent_observable_core/
  __init__.py          # Public API exports
  module_name.py       # Core implementation
  tests/
    __init__.py
    test_module_name.py  # Unit tests
```

### `__init__.py` Pattern

```python
"""Module docstring."""
from .module_name import (
    PublicClass,
    public_function,
    PublicConfig,
)

__all__ = [
    "PublicClass",
    "public_function",
    "PublicConfig",
]
```

### Test File Pattern

```python
"""Tests for module_name."""
import pytest
from unittest.mock import Mock, patch
from agent_observable_core.module_name import PublicClass, public_function


class TestPublicClass:
    """Test suite for PublicClass."""
    
    def test_initialization(self):
        """Test class initialization with defaults."""
        instance = PublicClass()
        assert instance is not None
    
    def test_initialization_with_config(self):
        """Test class initialization with custom config."""
        config = PublicConfig(custom_param="value")
        instance = PublicClass(config=config)
        assert instance._config.custom_param == "value"
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method."""
        instance = PublicClass()
        result = await instance.async_method("input")
        assert result is not None
    
    def test_error_handling(self):
        """Test error handling."""
        instance = PublicClass()
        with pytest.raises(SpecificError):
            instance.method_that_raises()
```

---

## API Contracts

### 1. Function Signatures

**Required:**
- Type hints for all parameters
- Return type annotation
- Optional parameters with defaults
- Docstring with Args, Returns, Raises

**Example:**
```python
def public_function(
    required_param: str,
    optional_param: Optional[int] = None,
    config: Optional[Config] = None,
) -> Optional[Result]:
    """Function description.
    
    Args:
        required_param: Description of required parameter
        optional_param: Description of optional parameter (default: None)
        config: Optional configuration (default: None)
        
    Returns:
        Result object or None if operation fails
        
    Raises:
        ValueError: If required_param is invalid
        TimeoutError: If operation times out
    """
    pass
```

### 2. Class Interfaces

**Required:**
- Public methods documented
- Private methods prefixed with `_`
- Properties for computed values
- Context managers where appropriate

**Example:**
```python
class PublicClass:
    """Public class interface."""
    
    @property
    def status(self) -> str:
        """Get current status."""
        return self._status
    
    def public_method(self) -> None:
        """Public method."""
        pass
    
    def _private_method(self) -> None:
        """Private method (implementation detail)."""
        pass
```

### 3. Configuration Objects

**Required:**
- `@dataclass` decorator
- Type hints for all fields
- Default values
- Factory methods for creating instances

**Example:**
```python
@dataclass
class MyConfig:
    """Configuration for MyClass."""
    param1: str = "default1"
    param2: int = 100
    param3: Optional[str] = None
    
    def create_instance(self) -> "MyClass":
        """Create MyClass instance with this config."""
        return MyClass(config=self)
```

---

## Error Handling

### 1. Exception Hierarchy

**Pattern:**
```python
class BaseAgentException(Exception):
    """Base exception for all agent-related errors."""
    error_code: str = "AGENT_ERROR"
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code or self.error_code
        self.details = details or {}
        logger.error(f"[{self.error_code}] {message}", extra=self.details)

class SpecificError(BaseAgentException):
    """Specific error type."""
    error_code: str = "SPECIFIC_ERROR"
```

### 2. Error Handling in Functions

**Pattern:**
```python
def function_with_error_handling(param: str) -> Optional[Result]:
    """Function with proper error handling."""
    try:
        # Validate input
        if not param:
            raise ValueError("param cannot be empty")
        
        # Perform operation
        result = _internal_operation(param)
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise
    except TimeoutError as e:
        logger.error(f"Timeout error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise SpecificError(f"Operation failed: {e}", details={"param": param})
```

### 3. Async Error Handling

**Pattern:**
```python
async def async_function_with_errors(param: str) -> Optional[Result]:
    """Async function with error handling."""
    try:
        result = await asyncio.wait_for(
            _async_operation(param),
            timeout=30.0
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out: {param}")
        raise TimeoutError(f"Operation exceeded timeout")
    except SpecificError:
        raise  # Re-raise specific errors
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

---

## Type Annotations

### Required Type Hints

**All functions must have:**
- Parameter type hints
- Return type hints
- Use `Optional[T]` for nullable types
- Use `Union[T, U]` for multiple types
- Use `Dict[str, Any]` for flexible dictionaries
- Use `List[T]` for lists
- Use `Callable` for function types

**Example:**
```python
from typing import Optional, Dict, List, Any, Callable, Awaitable

def typed_function(
    required: str,
    optional: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
    callback: Optional[Callable[[str], None]] = None,
) -> Optional[Dict[str, Any]]:
    """Function with complete type hints."""
    pass

async def async_typed_function(
    param: str,
) -> Awaitable[Optional[Result]]:
    """Async function with type hints."""
    pass
```

### Generic Types

**Use generics for reusable components:**
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    """Generic container."""
    def __init__(self, value: T) -> None:
        self._value = value
    
    def get(self) -> T:
        return self._value
```

---

## Testing Requirements

### 1. Test Coverage

**Required:**
- 90%+ code coverage
- All public APIs tested
- Error cases tested
- Edge cases tested
- Async functions tested with `@pytest.mark.asyncio`

### 2. Test Structure

**Pattern:**
```python
"""Tests for module_name."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from agent_observable_core.module_name import PublicClass


class TestPublicClass:
    """Test suite for PublicClass."""
    
    def test_initialization_defaults(self):
        """Test initialization with default config."""
        instance = PublicClass()
        assert instance is not None
    
    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = CustomConfig(param="value")
        instance = PublicClass(config=config)
        assert instance._config.param == "value"
    
    @pytest.mark.asyncio
    async def test_async_method_success(self):
        """Test async method success case."""
        instance = PublicClass()
        result = await instance.async_method("input")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_method_error(self):
        """Test async method error case."""
        instance = PublicClass()
        with pytest.raises(SpecificError):
            await instance.async_method("invalid")
    
    def test_error_handling(self):
        """Test error handling."""
        instance = PublicClass()
        with pytest.raises(ValueError):
            instance.method_with_validation("")
```

### 3. Mocking Patterns

**Pattern:**
```python
@patch('agent_observable_core.module_name.external_dependency')
def test_with_mock(mock_dependency):
    """Test with mocked dependency."""
    mock_dependency.return_value = "mocked_result"
    instance = PublicClass()
    result = instance.method_using_dependency()
    assert result == "mocked_result"
    mock_dependency.assert_called_once()

@pytest.mark.asyncio
async def test_async_with_mock():
    """Test async function with mock."""
    with patch('module.external_async') as mock_async:
        mock_async.return_value = AsyncMock(return_value="result")
        result = await async_function()
        assert result == "result"
```

---

## Documentation Standards

### 1. Module Docstrings

**Required:**
```python
"""Module purpose and framework-agnostic nature.

This module provides X, Y, Z functionality that works with
any agent framework (MS Agent Framework, LangGraph, OpenAI custom routing).

Key features:
- Feature 1
- Feature 2
- Feature 3

Example:
    >>> from agent_observable_core.module_name import PublicClass
    >>> instance = PublicClass()
    >>> result = instance.do_something()
"""
```

### 2. Class Docstrings

**Required:**
```python
class PublicClass:
    """Class purpose and usage.
    
    This class does X, Y, Z in a framework-agnostic way.
    
    Args:
        config: Optional configuration (uses defaults if None)
        
    Example:
        >>> config = MyConfig(param="value")
        >>> instance = PublicClass(config=config)
        >>> result = instance.method()
    """
```

### 3. Function Docstrings

**Required:**
```python
def public_function(
    param: str,
    optional: Optional[int] = None,
) -> Optional[Result]:
    """Function description.
    
    This function does X with Y, returning Z.
    
    Args:
        param: Description of parameter
        optional: Description of optional parameter (default: None)
        
    Returns:
        Result object or None if operation fails
        
    Raises:
        ValueError: If param is invalid
        TimeoutError: If operation times out
        
    Example:
        >>> result = public_function("input")
        >>> assert result is not None
    """
```

---

## Framework-Agnostic Design

### 1. Framework Detection

**Pattern:**
```python
class FrameworkDetector:
    """Detects which agent framework is being used."""
    
    @classmethod
    def detect(cls) -> AgentFramework:
        """Detect framework at runtime."""
        # Try MS Agent Framework
        try:
            import agent_framework
            if hasattr(agent_framework, 'WorkflowBuilder'):
                return AgentFramework.MS_AGENT_FRAMEWORK
        except ImportError:
            pass
        
        # Try LangGraph
        try:
            import langgraph
            return AgentFramework.LANGGRAPH
        except ImportError:
            pass
        
        return AgentFramework.UNKNOWN
```

### 2. Abstraction Layers

**Pattern:**
```python
class MiddlewareHooks:
    """Hooks for framework-specific extensions."""
    
    def extract_input_text(self, context: Any) -> Optional[str]:
        """Extract input text from any framework context."""
        # Try multiple patterns
        if hasattr(context, 'input'):
            return context.input
        if hasattr(context, 'message'):
            return context.message
        if isinstance(context, dict) and 'input' in context:
            return context['input']
        return None
    
    def extract_output_text(self, context: Any, result: Any) -> Optional[str]:
        """Extract output text from any framework result."""
        # Try multiple patterns
        if hasattr(result, 'text'):
            return result.text
        if hasattr(result, 'content'):
            return result.content
        if isinstance(result, str):
            return result
        return None
```

### 3. Standardization

**Pattern:**
```python
class MetricNameStandardizer:
    """Standardizes metric names across frameworks."""
    
    def __init__(self, service_name: str = "agent-service"):
        self.service_name = service_name
    
    def agent_invocations(self, agent_name: str) -> str:
        """Standard metric name for agent invocations."""
        return f"agent.{agent_name}.invocations"
    
    def workflow_runs(self) -> str:
        """Standard metric name for workflow runs."""
        return "workflow.runs"
```

---

## Example Specifications

### Example 1: New Metric Collector

**Specification:**
```
Create a new metric collector class that:
1. Extends MetricsCollector
2. Adds support for custom metric types
3. Maintains thread-safety
4. Provides framework-agnostic interface
5. Includes comprehensive tests
6. Follows all code patterns in this specification
```

**Generated Code Should:**
- Use `@dataclass` for configuration
- Use `threading.Lock` for thread-safety
- Have type hints for all methods
- Include docstrings with examples
- Have 90%+ test coverage
- Export via `__init__.py`

### Example 2: New Middleware Hook

**Specification:**
```
Add a new hook to MiddlewareHooks for:
1. Custom validation before agent execution
2. Framework-agnostic input validation
3. Integration with existing middleware
4. Error handling and metrics tracking
```

**Generated Code Should:**
- Extend `MiddlewareHooks` class
- Use `Optional` return types
- Handle framework differences
- Include error handling
- Add metrics tracking
- Include tests

### Example 3: New Exception Type

**Specification:**
```
Create a new exception type for:
1. Rate limiting errors
2. Extends BaseAgentException
3. Includes error code and details
4. Proper logging
```

**Generated Code Should:**
- Extend `BaseAgentException`
- Include `error_code` class variable
- Accept `details` dictionary
- Log errors appropriately
- Include in `__init__.py` exports
- Include tests

---

## Validation Checklist

Before submitting generated code, verify:

- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] All classes have docstrings
- [ ] All public APIs exported in `__init__.py`
- [ ] Tests have 90%+ coverage
- [ ] Code is framework-agnostic
- [ ] No hardcoded framework dependencies
- [ ] Uses standardized naming
- [ ] Error handling follows patterns
- [ ] Async functions use `asyncio.wait_for` for timeouts
- [ ] Thread-safe code uses locks
- [ ] Configuration via dataclasses
- [ ] Sensible defaults for all parameters
- [ ] Logging at appropriate levels
- [ ] No global state

---

## Quick Reference

### Import Patterns
```python
from __future__ import annotations
import logging
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
```

### Logging Pattern
```python
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

### Thread Safety
```python
import threading
self._lock = threading.Lock()

with self._lock:
    # Critical section
    pass
```

### Async Timeout
```python
import asyncio
result = await asyncio.wait_for(
    async_operation(),
    timeout=30.0
)
```

### Context Variables
```python
from contextvars import ContextVar
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
```

---

## Conclusion

This specification ensures all generated code follows the same patterns, architecture, and standards as the existing `agent-observable-core` library. Use this document to guide LLM code generation or train developers on the codebase patterns.

**Key Principles:**
1. Framework-agnostic design
2. Zero-configuration defaults
3. Automatic instrumentation
4. Standardized naming
5. Comprehensive testing
6. Complete documentation

**When in doubt:** Follow existing code patterns in `libraries/agent-observable-core/src/agent_observable_core/`.

**Usage Example:**
```
Prompt to LLM:
"Using the CODE_GENERATION_SPECIFICATION.md, create a new module for 
[feature description]. Follow all patterns, include tests, and ensure 
framework-agnostic design."
```
