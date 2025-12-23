# Detailed Refactoring Plan: Enterprise Shared Library

**Status as of v0.01 (`agent-observable`)**
- **Architecture decision**: Micro-library approach, implemented as a **monorepo** (`agent-observable` root) with `libraries/agent-observable-*` and `examples/taskpilot/`.
- **Frameworks**: Still integrates with MS Agent Framework via adapters; design remains framework-agnostic.
- **Execution plan**: We are using the 2-week Phase 0 sprint from `IMPLEMENTATION_TRACKER.md` as the immediate plan; this document describes the full multi-phase roadmap.
- **Must-have features**: Canonical, up-to-date prioritization lives in `MUST_HAVE_FEATURES.md` and `IMPLEMENTATION_TRACKER.md`.

## Executive Summary

**Goal**: Refactor existing code to work with MS Agent Framework while maintaining all functionality, and prepare for future decision on micro-libraries vs. framework-agnostic unified approach.

**Strategy**: **Incremental, non-breaking refactoring** with clear decision points.

**Timeline**: 12-16 weeks (3-4 months)

**Risk**: **Low** - Each phase is independently testable, backward compatible

---

## Must-Have Features from Capability Matrix

**See [MUST_HAVE_FEATURES.md](MUST_HAVE_FEATURES.md) for complete analysis.**

### Critical Priority (Must Have - P0)

From `CAPABILITIES_MATRIX.md` and `MICROSOFT_AGENT_FRAMEWORK_BEST_PRACTICES.md`:

1. **Rate Limiting** (Infrastructure) - Security & Stability
   - ✅ **Use cloud infrastructure service (Azure APIM / AWS API Gateway)**
   - No custom implementation needed
   - Configure at infrastructure level (per-user, global limits)
   - Note: API rate limit handling (429 detection) still needed for external API calls

2. **Tool Execution Timeouts** (Critical) - Reliability ✅ **WILL IMPLEMENT**
   - Configurable timeout per tool (default: 30s)
   - Graceful timeout handling (don't crash workflow)
   - Timeout events logged as policy decisions
   - Timeout metrics
   - **Planned for Phase 2, Week 7**

3. **Retry Logic with Exponential Backoff** (Critical) - Reliability ✅ **WILL IMPLEMENT**
   - Retry decorator with exponential backoff
   - Retry on API failures (transient errors)
   - Retry on rate limits (429 status)
   - Retry metrics
   - Configurable max attempts and backoff factor
   - **Planned for Phase 2, Week 8**

4. **Token/Cost Tracking Verification** (Critical) - Cost Management ✅ **WILL IMPLEMENT**
   - Verify `llm_cost_tracker.py` is actually used
   - Ensure token counting works correctly
   - Add cost metrics to observability system
   - Create cost dashboard/viewer
   - Document cost tracking usage
   - **Planned for Phase 2, Week 9**

### High Priority (Should Have - P1)

5. **Response Caching** (High) - Cost Optimization ✅ **WILL IMPLEMENT**
   - Configurable timeout per tool (default: 30s)
   - Graceful timeout handling (don't crash workflow)
   - Timeout events logged as policy decisions
   - Timeout metrics
   - **Planned for Phase 2, Week 7**

3. **Retry Logic with Exponential Backoff** (Critical) - Reliability ✅ **WILL IMPLEMENT**
   - Retry decorator with exponential backoff
   - Retry on API failures (transient errors)
   - Retry on rate limits (429 status)
   - Retry metrics
   - Configurable max attempts and backoff factor
   - **Planned for Phase 2, Week 8**

4. **Token/Cost Tracking Verification** (Critical) - Cost Management ✅ **WILL IMPLEMENT**
   - Verify `llm_cost_tracker.py` is actually used
   - Ensure token counting works correctly
   - Add cost metrics to observability system
   - Create cost dashboard/viewer
   - Document cost tracking usage
   - **Planned for Phase 2, Week 9**

### High Priority (Should Have - P1)

5. **Response Caching** (High) - Cost Optimization ✅ **WILL IMPLEMENT**
   - Cache layer (Redis or in-memory)
   - Cache key based on input hash
   - Configurable TTL per agent/query type
   - Cache hit/miss metrics
   - Invalidate cache on prompt updates
   - **Planned for Phase 2.5 (optional, high value)**

6. **Context Window Management** (High) - Functionality ✅ **WILL IMPLEMENT**
   - Track context window usage per conversation
   - Implement truncation strategy (keep recent, summarize old)
   - Add context summarization (LLM-based)
   - Configurable context limits per agent
   - Context usage metrics
   - **Planned for Phase 2.5 (optional, high value)**

7. **API Rate Limit Handling** (High) - Reliability ✅ **WILL IMPLEMENT**
   - Detect rate limit errors (429 status)
   - Implement exponential backoff on rate limits
   - Add rate limit queue (defer requests)
   - Track rate limit usage per model
   - Alert on approaching rate limits
   - **Planned for Phase 2.5 (optional, high value)**

### Medium Priority (Nice to Have - P2)

8. **Exception Hierarchy & Error Codes** (Medium) - Developer Experience ✅ **WILL IMPLEMENT**
   - Base exception classes (hierarchy)
   - Error code system (e.g., `AGENT_001`, `TOOL_002`)
   - User-friendly error messages
   - Error codes in logs
   - **Planned for future phase (enhancement)**

9. **Advanced Prompt Injection Detection** (Medium) - Security Enhancement
   - Pattern-based injection detection
   - Instruction override detection
   - Role confusion detection

10. **Input Sanitization** (Medium) - Security Enhancement
    - Remove control characters
    - Normalize encoding (UTF-8 validation)
    - Validate character sets

---

## Phase-by-Phase Refactoring Plan

### Phase 0: Foundation & Preparation (Week 1-2)

**Goal**: Set up refactoring infrastructure without breaking anything.

#### 0.1 Create Abstraction Interfaces (No Breaking Changes)

**Location**: `src/core/interfaces/` (new directory)

**Files to Create**:
```
src/core/interfaces/
├── __init__.py
├── agent.py          # AgentExecutionContext, AgentInterface (abstract)
├── middleware.py     # MiddlewareInterface (abstract)
└── workflow.py       # WorkflowInterface (abstract)
```

**Implementation**:
- Define abstract base classes/interfaces
- Keep existing code working (no changes to existing files)
- These interfaces will be used later for framework-agnostic design

**Testing**:
- Verify existing code still works
- No functional changes

**Decision Point**: None - pure preparation

---

#### 0.2 Extract Configuration to Dependency Injection

**Location**: `src/core/config/` (new directory)

**Goal**: Remove hard-coded config access, use dependency injection.

**Current Problem**:
```python
# Current: Hard-coded config access
from taskpilot.core.config import get_paths
paths = get_paths()
metrics_file = paths.metrics_file
```

**Refactored**:
```python
# New: Config injected via constructor
class MetricsCollector:
    def __init__(self, config: MetricsConfig):
        self.config = config  # Injected, not from global
```

**Files to Refactor**:
- `src/core/observability.py` - MetricsCollector
- `src/core/guardrails/decision_logger.py` - DecisionLogger
- `src/core/otel_integration.py` - OpenTelemetry init

**Changes**:
1. Add `Config` parameter to constructors
2. Keep global functions for backward compatibility
3. Global functions use default config (backward compatible)

**Testing**:
- All existing tests pass
- New code can use dependency injection
- Old code still works

**Decision Point**: None - backward compatible

---

#### 0.3 Remove Hard-Coded Paths

**Location**: All files with hard-coded paths

**Goal**: All paths come from config, not hard-coded.

**Files to Update**:
- `src/core/observability.py` - Remove `Path(__file__).parent.parent.parent`
- `src/core/guardrails/decision_logger.py` - Remove hard-coded paths
- `src/core/prompt_loader.py` - Remove hard-coded paths

**Changes**:
1. Use `config.paths` instead of hard-coded paths
2. Keep fallbacks for backward compatibility
3. Log warnings when using fallbacks

**Testing**:
- Verify paths resolve correctly
- Verify fallbacks work
- All existing functionality preserved

**Decision Point**: None - backward compatible

---

### Phase 1: Extract Core Libraries (Week 3-6)

**Goal**: Extract observability, policy, prompts into reusable libraries while keeping MS Agent Framework integration working.

**Strategy**: Create new libraries alongside existing code, migrate incrementally.

---

#### 1.1 Extract Observability Core Library

**Location**: `src/lib/observability/` (new directory)

**Structure**:
```
src/lib/observability/
├── __init__.py
├── metrics/
│   ├── __init__.py
│   ├── collector.py          # MetricsCollector (no app deps)
│   └── exporter.py           # Prometheus/OTLP exporters
├── tracing/
│   ├── __init__.py
│   ├── tracer.py             # Tracer (no app deps)
│   └── otel_integration.py   # OpenTelemetry (no app deps)
├── logging/
│   ├── __init__.py
│   └── structured_logger.py  # Structured logger (no app deps)
└── config/
    └── observability_config.py  # Configuration dataclasses
```

**Key Changes**:
1. **Remove all `taskpilot` imports**
2. **Remove all hard-coded paths**
3. **Use dependency injection** (config passed to constructors)
4. **No global singletons** (instances created by caller)

**Example**:
```python
# Before (current)
from taskpilot.core.config import get_paths
paths = get_paths()
metrics_file = paths.metrics_file
_metrics_collector = MetricsCollector(metrics_file=metrics_file)

# After (new library)
from taskpilot.lib.observability import MetricsCollector, ObservabilityConfig

config = ObservabilityConfig(metrics_file=Path("metrics.json"))
collector = MetricsCollector(config=config)  # No globals, no hard-coded paths
```

**Integration with Existing Code**:
- Create adapter in `src/core/observability.py`:
  ```python
  # Adapter: Wraps new library for backward compatibility
  from taskpilot.lib.observability import MetricsCollector as NewMetricsCollector
  from taskpilot.core.config import get_paths
  
  def get_metrics_collector():
      """Backward compatible wrapper."""
      global _metrics_collector
      if _metrics_collector is None:
          paths = get_paths()
          config = ObservabilityConfig(metrics_file=paths.metrics_file)
          _metrics_collector = NewMetricsCollector(config=config)
      return _metrics_collector
  ```

**Testing**:
- New library has its own tests (no app dependencies)
- Existing code still works via adapter
- Both can coexist

**Decision Point**: None - pure extraction, backward compatible

---

#### 1.2 Extract Policy Core Library

**Location**: `src/lib/policy/` (new directory)

**Structure**:
```
src/lib/policy/
├── __init__.py
├── decision/
│   ├── __init__.py
│   ├── types.py              # DecisionType, DecisionResult
│   ├── models.py              # PolicyDecision
│   └── logger.py              # DecisionLogger (no app deps)
├── opa/
│   ├── __init__.py
│   ├── embedded.py            # Embedded OPA
│   └── validator.py           # OPA validator
└── config/
    └── policy_config.py       # Policy configuration
```

**Key Changes**:
1. Remove all `taskpilot` imports
2. Remove hard-coded paths
3. Use dependency injection
4. No global singletons

**Integration**:
- Create adapter in `src/core/guardrails/decision_logger.py` for backward compatibility

**Testing**:
- New library has its own tests
- Existing code works via adapter

**Decision Point**: None - pure extraction

---

#### 1.3 Extract Prompt Management Library

**Location**: `src/lib/prompts/` (new directory)

**Structure**:
```
src/lib/prompts/
├── __init__.py
├── manager.py                 # PromptManager (no app deps)
├── loader.py                  # Prompt file loader
├── validator.py               # NeMo Guardrails validation
└── versioning.py              # Version management
```

**Key Changes**:
1. Remove all `taskpilot` imports
2. Remove hard-coded paths
3. Use dependency injection
4. Support versioning

**Integration**:
- Create adapter in `src/core/prompt_loader.py` for backward compatibility

**Testing**:
- New library has its own tests
- Existing code works via adapter

**Decision Point**: None - pure extraction

---

### Phase 2: Add Must-Have Features (Week 7-10)

**Goal**: Add critical features identified in capability matrix while maintaining MS Agent Framework compatibility.

---

#### 2.1 Rate Limiting (Infrastructure) - Use Azure APIM / AWS API Gateway

**Status**: ✅ **Use Cloud Infrastructure** - No custom implementation needed

**Decision**: Configure rate limiting at infrastructure level using Azure API Management (APIM) or AWS API Gateway.

**Configuration**:
- Configure per-user rate limiting in APIM policies
- Configure global rate limiting in APIM policies
- No application code changes needed

**Note**: API rate limit handling (detecting 429 responses from external APIs and retrying) is different and handled in "Retry Logic" feature (section 2.2).

---

#### 2.1 Tool Execution Timeouts (Critical) ✅ **WILL IMPLEMENT**

**Location**: `src/core/tool_executor.py` (enhance existing)

**Implementation**:
```python
async def execute_tool_with_timeout(
    tool_func: Callable,
    tool_name: str,
    timeout_seconds: float = 30.0,
    **kwargs
) -> Any:
    """Execute tool with timeout."""
    try:
        return await asyncio.wait_for(
            tool_func(**kwargs),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        # Log as policy decision
        await log_timeout_decision(tool_name, timeout_seconds)
        raise ToolTimeoutError(f"Tool {tool_name} timed out after {timeout_seconds}s")
```

**Integration**:
- Update `tool_executor.py` to use timeout wrapper
- Log timeouts as policy decisions
- Add timeout metrics

**Configuration**:
```python
@dataclass
class TimeoutConfig:
    default_timeout: float = 30.0  # seconds
    tool_timeouts: Dict[str, float] = field(default_factory=dict)  # per-tool
    enabled: bool = True
```

**Testing**:
- Test timeout behavior
- Test graceful handling
- Verify policy decisions logged

**Decision Point**: None - new feature

---

#### 2.2 Retry Logic with Exponential Backoff (Critical) ✅ **WILL IMPLEMENT**

**Location**: `src/lib/observability/retry.py` (new)

**Implementation**:
```python
def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator
```

**Integration**:
- Apply to LLM client calls
- Apply to OPA validation calls
- Add retry metrics

**Configuration**:
```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    enabled: bool = True
```

**Testing**:
- Test retry behavior
- Test backoff timing
- Test max attempts

**Decision Point**: None - new feature

---

#### 2.3 Verify & Enhance Token/Cost Tracking (Critical) ✅ **WILL IMPLEMENT**

**Location**: `src/core/llm_cost_tracker.py` (enhance existing)

**Current State**: Code exists but usage unclear.

**Actions**:
1. **Verify usage**: Check if `track_llm_metrics()` is called
2. **Enhance if needed**: Ensure token counting works correctly
3. **Add to observability**: Integrate with metrics system
4. **Create dashboard**: Cost tracking viewer

**Integration**:
- Ensure called in middleware
- Add cost metrics to observability
- Create cost dashboard/viewer

**Testing**:
- Verify token counting accuracy
- Verify cost calculation
- Test cost metrics

**Decision Point**: None - verification and enhancement

---

### Phase 3: MS Agent Framework Integration Layer (Week 11-12)

**Goal**: Create clean integration layer for MS Agent Framework while keeping everything working.

---

#### 3.1 Create MS Agent Framework Adapter

**Location**: `src/core/adapters/ms_agent_framework.py` (new)

**Purpose**: Bridge MS Agent Framework to our interfaces (preparation for framework-agnostic).

**Implementation**:
```python
from agent_framework import AgentRunContext as MSContext
from taskpilot.core.interfaces import AgentExecutionContext

class MSAgentFrameworkAdapter:
    """Adapter for MS Agent Framework."""
    
    @staticmethod
    def adapt_context(ms_context: MSContext) -> AgentExecutionContext:
        """Convert MS context to our interface."""
        return AdaptedMSContext(ms_context)

class AdaptedMSContext(AgentExecutionContext):
    """Adapter wrapping MS Agent Framework context."""
    # Implement all interface methods
```

**Integration**:
- Use adapter in middleware (optional - can use directly)
- Keep existing code working
- Adapter is optional (for future framework-agnostic)

**Testing**:
- Test adapter conversion
- Test with existing middleware
- Verify no breaking changes

**Decision Point**: **Optional** - Can skip if not doing framework-agnostic

---

#### 3.2 Refactor Middleware to Use New Libraries

**Location**: `src/core/middleware.py` (refactor existing)

**Goal**: Use extracted libraries instead of direct imports.

**Current**:
```python
# Current: Direct imports
from taskpilot.core.observability import get_metrics_collector
from taskpilot.core.guardrails.decision_logger import get_decision_logger
```

**Refactored**:
```python
# New: Use libraries via dependency injection
from taskpilot.lib.observability import MetricsCollector
from taskpilot.lib.policy import DecisionLogger

class UnifiedMiddleware:
    def __init__(
        self,
        metrics: MetricsCollector,  # Injected
        decision_logger: DecisionLogger,  # Injected
        rate_limiter: RateLimiter,  # Injected
        config: MiddlewareConfig  # Injected
    ):
        self.metrics = metrics
        self.decision_logger = decision_logger
        self.rate_limiter = rate_limiter
```

**Backward Compatibility**:
- Keep `create_audit_and_policy_middleware()` function
- Function creates instances and injects them
- Existing code unchanged

**Testing**:
- All existing tests pass
- New code uses dependency injection
- Old code still works

**Decision Point**: None - backward compatible refactor

---

### Phase 4: Decision Point - Architecture Choice (Week 13)

**Goal**: Make decision on micro-libraries vs. unified framework approach.

**Options**:

#### Option A: Micro-Libraries (Recommended for Enterprise)

**Structure**:
```
taskpilot-libs/
├── agent-observability-core/     # Just metrics, traces, logs
├── agent-policy-core/            # Just policy decisions
├── agent-guardrails-core/        # Just guardrails
├── agent-prompts-core/           # Just prompt management
└── agent-framework-ms/           # MS Agent Framework integration
```

**Pros**:
- ✅ Smaller surface area = fewer breaking changes
- ✅ Teams only install what they need
- ✅ Independent versioning
- ✅ Easier maintenance

**Cons**:
- ❌ More packages to manage
- ❌ Teams need to understand multiple packages

**If Chosen**: Continue with Phase 5A

---

#### Option B: Unified Framework (Current Plan)

**Structure**:
```
agent-framework-observable/
├── core/              # Framework-agnostic core
├── adapters/          # Framework adapters
└── plugins/           # Optional plugins
```

**Pros**:
- ✅ Single package
- ✅ "Batteries included"
- ✅ Easier for new projects

**Cons**:
- ❌ Larger surface area
- ❌ All-or-nothing updates
- ❌ Harder to maintain

**If Chosen**: Continue with Phase 5B

---

### Phase 5A: Micro-Libraries Path (Week 14-16)

**If Option A chosen**:

#### 5A.1 Package Extraction

1. **Create separate packages**:
   - `agent-observability-core/` (from `src/lib/observability/`)
   - `agent-policy-core/` (from `src/lib/policy/`)
   - `agent-prompts-core/` (from `src/lib/prompts/`)

2. **Create MS Agent Framework integration package**:
   - `agent-framework-ms/` (wraps MS Agent Framework with observability)

3. **Update existing code**:
   - Use packages as dependencies
   - Remove extracted code from `src/lib/`

**Testing**:
- Each package has its own tests
- Integration tests verify packages work together
- Existing code works with new packages

---

### Phase 5B: Unified Framework Path (Week 14-16)

**If Option B chosen**:

#### 5B.1 Create Unified Framework

1. **Create `AgentFramework` class**:
   - Wraps all libraries
   - Provides simple API
   - Auto-configures everything

2. **Create adapters** (if framework-agnostic):
   - MS Agent Framework adapter
   - LangGraph adapter (optional)
   - Role-routing adapter (optional)

3. **Update existing code**:
   - Use framework instead of direct library calls
   - Keep backward compatibility

**Testing**:
- Framework works with MS Agent Framework
- All existing functionality preserved
- New projects can use framework

---

## Critical Features Integration

**Note**: Rate limiting handled by cloud infrastructure (Azure APIM / AWS API Gateway). Configure at infrastructure level.

### Timeout Integration

**Where**: Tool Execution

```python
# In tool_executor.py
async def execute_tool(tool_func, tool_name, **kwargs):
    timeout = self.config.get_tool_timeout(tool_name)
    
    try:
        return await asyncio.wait_for(
            tool_func(**kwargs),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        # Log as policy decision
        await decision_logger.log_decision(
            PolicyDecision.create(
                decision_type=DecisionType.TOOL_TIMEOUT,
                result=DecisionResult.DENY,
                reason=f"Tool {tool_name} timed out after {timeout}s"
            )
        )
        raise ToolTimeoutError(...)
```

### Retry Integration

**Where**: LLM Client Calls

```python
# In agent execution
@retry_with_backoff(
    max_attempts=3,
    retryable_exceptions=(APIError, RateLimitError)
)
async def call_llm(messages, **kwargs):
    # LLM call with automatic retry
    return await client.chat.completions.create(...)
```

---

## Testing Strategy

### Phase 0-1: Backward Compatibility Tests

**Goal**: Ensure no breaking changes.

**Tests**:
- All existing unit tests pass
- All existing integration tests pass
- No functional changes

### Phase 2: Feature Tests

**Goal**: Verify new features work.

**Tests**:
- Rate limiting tests
- Timeout tests
- Retry tests
- Cost tracking tests

### Phase 3-5: Integration Tests

**Goal**: Verify everything works together.

**Tests**:
- End-to-end workflow tests
- MS Agent Framework integration tests
- Performance tests (overhead measurement)

---

## Migration Path for Existing Code

### Step 1: Use New Libraries (Optional)

**Teams can gradually migrate**:

```python
# Old way (still works)
from taskpilot.core.observability import get_metrics_collector
metrics = get_metrics_collector()

# New way (optional)
from taskpilot.lib.observability import MetricsCollector, ObservabilityConfig
config = ObservabilityConfig(metrics_file=Path("metrics.json"))
metrics = MetricsCollector(config=config)
```

### Step 2: Use Unified Framework (If Chosen)

```python
# New projects can use framework
from agent_framework_observable import AgentFramework

framework = AgentFramework(service_name="my_app")
agent = framework.wrap_agent(ms_agent, name="MyAgent", prompt="planner")
```

### Step 3: Complete Migration (Future)

**When ready**:
- Remove old implementations
- Update all imports
- Remove adapters

---

## Risk Mitigation

### Risk 1: Breaking Changes

**Mitigation**:
- All changes backward compatible
- Adapters maintain old API
- Gradual migration path

### Risk 2: Performance Regression

**Mitigation**:
- Performance tests in CI
- Overhead budget (< 5%)
- Feature flags to disable expensive features

### Risk 3: Version Conflicts

**Mitigation**:
- Minimal dependencies in core
- Optional dependencies via extras
- Version compatibility matrix

---

## Success Criteria

### Phase 0-1: Foundation
- ✅ All existing tests pass
- ✅ No breaking changes
- ✅ Libraries extracted with zero app dependencies
- ✅ Backward compatibility maintained

### Phase 2: Features
- ✅ Rate limiting implemented and tested
- ✅ Timeouts implemented and tested
- ✅ Retry logic implemented and tested
- ✅ Cost tracking verified and enhanced

### Phase 3-5: Integration
- ✅ MS Agent Framework integration works
- ✅ All features integrated
- ✅ Performance overhead < 5%
- ✅ Documentation complete

---

## Timeline Summary

| Phase | Duration | Goal | Risk | Must-Have Features |
|-------|----------|------|------|-------------------|
| **Phase 0** | 2 weeks | Foundation & preparation | Low | None |
| **Phase 1** | 4 weeks | Extract core libraries | Low | None |
| **Phase 2** | 4 weeks | Add must-have features | Medium | **All P0 features** |
| **Phase 3** | 2 weeks | MS Agent Framework integration | Low | None |
| **Phase 4** | 1 week | Architecture decision | N/A | None |
| **Phase 5A/5B** | 3 weeks | Final architecture | Low | None |
| **Total** | **15 weeks** | Complete refactoring | **Low-Medium** | **3 critical features** (rate limiting via infrastructure) |

**Note**: Phase 2 includes all critical (P0) must-have features. High priority (P1) features can be added in Phase 2.5 if time permits.

---

## Decision Points

### Decision Point 1: After Phase 1 (Week 6)

**Question**: Continue with unified framework or switch to micro-libraries?

**Criteria**:
- Library extraction successful?
- Zero dependencies achieved?
- Backward compatibility maintained?

**Options**:
- Continue to Phase 2 (add features)
- Switch to micro-libraries approach

---

### Decision Point 2: After Phase 2 (Week 10)

**Question**: Proceed with framework-agnostic adapters or keep MS Agent Framework only?

**Criteria**:
- Must-have features implemented?
- Performance acceptable?
- Ready for enterprise use?

**Options**:
- Continue to Phase 3 (framework-agnostic)
- Skip Phase 3 (MS Agent Framework only)

---

### Decision Point 3: After Phase 3 (Week 12)

**Question**: Micro-libraries or unified framework?

**Criteria**:
- Enterprise requirements met?
- Maintenance burden acceptable?
- Team preferences?

**Options**:
- Phase 5A: Micro-libraries
- Phase 5B: Unified framework

---

## Next Steps

1. **Review this plan** - Does it meet requirements?
2. **Prioritize phases** - Which phases are most critical?
3. **Clarify must-haves** - Any additional features needed?
4. **Start Phase 0** - Begin foundation work

---

## Appendix: Must-Have Features Checklist

### Critical Priority (P0) - Must Have for Production
- [ ] Rate limiting (user, tool, global) - **Phase 2, Week 7**
- [ ] Tool execution timeouts - **Phase 2, Week 8**
- [ ] Retry logic with exponential backoff - **Phase 2, Week 9**
- [ ] Token/cost tracking verification - **Phase 2, Week 10**

### High Priority (P1) - Should Have
- [x] Response caching - ✅ **WILL IMPLEMENT** - **Phase 2.5 (optional, high value)**
- [x] Context window management - ✅ **WILL IMPLEMENT** - **Phase 2.5 (optional, high value)**
- [x] API rate limit handling (429 detection & retry) - ✅ **WILL IMPLEMENT** - **Phase 2.5 (optional, high value)** - Note: Different from infrastructure rate limiting; this handles external API responses

### Medium Priority (P2) - Nice to Have
- [x] Exception hierarchy & error codes - ✅ **WILL IMPLEMENT** - **Future phase (enhancement)**
- [ ] Schema versioning - **Future**
- [ ] Advanced prompt injection detection - **Future**

---

## Key Design Principles

### 1. **Backward Compatibility First**
- All changes maintain existing API
- Adapters bridge old and new code
- Gradual migration path

### 2. **Zero Breaking Changes**
- Existing code continues to work
- New code can use new libraries
- Both can coexist

### 3. **Incremental & Testable**
- Each phase independently testable
- Can stop at any phase
- Clear success criteria

### 4. **MS Agent Framework Compatible**
- All phases work with MS Agent Framework
- No framework changes required
- Existing workflows continue to work

### 5. **Future-Proof Architecture**
- Prepares for framework-agnostic design
- Can switch to micro-libraries later
- Can switch to unified framework later
- Decision deferred to Phase 4

---

*This plan is designed to be executed incrementally with minimal risk. Each phase is independently testable and backward compatible. All must-have features from capability matrix are included in Phase 2. Rate limiting handled by cloud infrastructure (Azure APIM / AWS API Gateway) to avoid overengineering.*
