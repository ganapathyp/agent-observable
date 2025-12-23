# Implementation Tracker - 2 Week Sprint

**Project**: `agent-observable` (micro-library approach)

**Goal**: Complete all Phase 0 changes in 2 weeks for socialization baseline.

**Timeline**: **2 weeks total** - aggressive timeline, iterate directly.

**Principle**: Every change must have solid testing before review. No exceptions.

**Micro-Library Structure** (Post 2-week sprint):
- `agent-observable-core/` - Observability (metrics, traces, logs)
- `agent-observable-policy/` - Policy decisions & OPA
- `agent-observable-guardrails/` - Guardrails (NeMo, validation)
- `agent-observable-prompts/` - Prompt management
- `agent-observable-ms/` - MS Agent Framework integration

---

## Phase 0: Foundation + Critical Features (2 Weeks - ALL CHANGES)

**Target**: Complete working baseline for socialization in 2 weeks

**Week 1 Focus**: Foundation (Interfaces, DI, Remove Hard-Coded Paths)
**Week 2 Focus**: Critical Features (Timeouts, Retry Logic)

### 0.1 Create Abstraction Interfaces

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `src/core/interfaces/` directory | ⬜ Pending | ⬜ | No breaking changes |
| Define `AgentExecutionContext` interface | ⬜ Pending | ⬜ | Abstract base class |
| Define `AgentInterface` interface | ⬜ Pending | ⬜ | Abstract base class |
| Define `MiddlewareInterface` interface | ⬜ Pending | ⬜ | Abstract base class |
| Define `WorkflowInterface` interface | ⬜ Pending | ⬜ | Abstract base class |
| Unit tests for interfaces | ⬜ Pending | ⬜ | Verify interfaces work |
| Integration test: existing code still works | ⬜ Pending | ⬜ | No functional changes |

**Completion**: 0/7 (0%)

---

### 0.2 Extract Configuration to Dependency Injection

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `src/core/config/` directory structure | ⬜ Pending | ⬜ | New directory |
| Refactor `MetricsCollector` to use DI | ⬜ Pending | ⬜ | Add Config parameter |
| Refactor `DecisionLogger` to use DI | ⬜ Pending | ⬜ | Add Config parameter |
| Refactor `OpenTelemetry` init to use DI | ⬜ Pending | ⬜ | Add Config parameter |
| Keep global functions for backward compatibility | ⬜ Pending | ⬜ | Critical - no breaking changes |
| Unit tests: new DI approach | ⬜ Pending | ⬜ | Test DI works |
| Integration tests: old code still works | ⬜ Pending | ⬜ | Test backward compatibility |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/8 (0%)

---

### 0.3 Remove Hard-Coded Paths

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Audit all hard-coded paths | ⬜ Pending | ⬜ | Find all instances |
| Update `observability.py` to use config paths | ⬜ Pending | ⬜ | Remove `Path(__file__).parent...` |
| Update `decision_logger.py` to use config paths | ⬜ Pending | ⬜ | Remove hard-coded paths |
| Update `prompt_loader.py` to use config paths | ⬜ Pending | ⬜ | Remove hard-coded paths |
| Add fallbacks for backward compatibility | ⬜ Pending | ⬜ | Log warnings when using fallbacks |
| Unit tests: paths resolve correctly | ⬜ Pending | ⬜ | Test path resolution |
| Integration tests: fallbacks work | ⬜ Pending | ⬜ | Test backward compatibility |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/8 (0%)

---

### 0.4 Implement Tool Execution Timeouts (Critical Feature)

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `TimeoutConfig` dataclass | ⬜ Pending | ⬜ | Configurable per tool |
| Implement `execute_tool_with_timeout()` function | ⬜ Pending | ⬜ | Use `asyncio.wait_for` |
| Update `tool_executor.py` to use timeout wrapper | ⬜ Pending | ⬜ | Integrate timeout logic |
| Log timeout events as policy decisions | ⬜ Pending | ⬜ | Decision logging integration |
| Add timeout metrics | ⬜ Pending | ⬜ | Metrics collection |
| Unit tests: timeout behavior | ⬜ Pending | ⬜ | Test timeout triggers |
| Unit tests: graceful handling | ⬜ Pending | ⬜ | Test no crashes |
| Integration tests: timeout in workflow | ⬜ Pending | ⬜ | Test end-to-end |
| Verify policy decisions logged | ⬜ Pending | ⬜ | Test decision logging |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/10 (0%)

---

### 0.5 Implement Retry Logic with Exponential Backoff (Critical Feature)

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `RetryConfig` dataclass | ⬜ Pending | ⬜ | Configurable retry params |
| Implement `retry_with_backoff()` decorator | ⬜ Pending | ⬜ | Exponential backoff |
| Apply to LLM client calls | ⬜ Pending | ⬜ | Integrate with OpenAI client |
| Apply to OPA validation calls | ⬜ Pending | ⬜ | Integrate with OPA |
| Add retry metrics | ⬜ Pending | ⬜ | Track retry attempts |
| Unit tests: retry behavior | ⬜ Pending | ⬜ | Test retry logic |
| Unit tests: backoff timing | ⬜ Pending | ⬜ | Test exponential backoff |
| Unit tests: max attempts | ⬜ Pending | ⬜ | Test failure after max attempts |
| Integration tests: retry in workflow | ⬜ Pending | ⬜ | Test end-to-end |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/10 (0%)

---

### Phase 0 Summary

| Category | Tasks | Completed | Pending | Completion |
|----------|-------|-----------|---------|------------|
| Interfaces | 7 | 0 | 7 | 0% |
| Dependency Injection | 8 | 0 | 8 | 0% |
| Remove Hard-Coded Paths | 8 | 0 | 8 | 0% |
| Tool Timeouts | 10 | 0 | 10 | 0% |
| Retry Logic | 10 | 0 | 10 | 0% |
| **Total** | **43** | **0** | **43** | **0%** |

---

## Phase 1: Library Extraction (Post 2-Week Sprint)

**Target**: Extract micro-libraries as `agent-observable-*` packages

**Micro-Library Structure**:
- `agent-observable-core/` - Observability library
- `agent-observable-policy/` - Policy library
- `agent-observable-guardrails/` - Guardrails library
- `agent-observable-prompts/` - Prompt management library

### 1.1 Extract Observability Core Library

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `src/lib/observability/` directory | ⬜ Pending | ⬜ | New library structure |
| Extract `MetricsCollector` (zero app deps) | ⬜ Pending | ⬜ | Remove all `taskpilot` imports |
| Extract `Tracer` (zero app deps) | ⬜ Pending | ⬜ | Remove all `taskpilot` imports |
| Extract `OpenTelemetry` integration (zero app deps) | ⬜ Pending | ⬜ | Remove all `taskpilot` imports |
| Extract structured logger (zero app deps) | ⬜ Pending | ⬜ | Remove all `taskpilot` imports |
| Create `ObservabilityConfig` dataclass | ⬜ Pending | ⬜ | Configuration only |
| Create adapter in `src/core/observability.py` | ⬜ Pending | ⬜ | Backward compatibility |
| Library unit tests (no app dependencies) | ⬜ Pending | ⬜ | Test library in isolation |
| Integration tests: existing code works via adapter | ⬜ Pending | ⬜ | Test backward compatibility |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/10 (0%)

---

### 1.2 Extract Policy Core Library

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `src/lib/policy/` directory | ⬜ Pending | ⬜ | New library structure |
| Extract `DecisionLogger` (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Extract `PolicyDecision` models (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Extract OPA validator (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Create `PolicyConfig` dataclass | ⬜ Pending | ⬜ | Configuration only |
| Create adapter in `src/core/guardrails/` | ⬜ Pending | ⬜ | Backward compatibility |
| Library unit tests (no app dependencies) | ⬜ Pending | ⬜ | Test library in isolation |
| Integration tests: existing code works via adapter | ⬜ Pending | ⬜ | Test backward compatibility |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/9 (0%)

---

### 1.3 Extract Prompt Management Library

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Create `src/lib/prompts/` directory | ⬜ Pending | ⬜ | New library structure |
| Extract `PromptManager` (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Extract prompt loader (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Extract NeMo Guardrails validator (zero app deps) | ⬜ Pending | ⬜ | Remove all app-specific imports |
| Add versioning support | ⬜ Pending | ⬜ | Version management |
| Create `PromptConfig` dataclass | ⬜ Pending | ⬜ | Configuration only |
| Create adapter in `src/core/prompt_loader.py` | ⬜ Pending | ⬜ | Backward compatibility |
| Library unit tests (no app dependencies) | ⬜ Pending | ⬜ | Test library in isolation |
| Integration tests: existing code works via adapter | ⬜ Pending | ⬜ | Test backward compatibility |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/9 (0%)

---

### 1.4 Migrate Features to New Libraries

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Migrate timeout feature to use new libraries | ⬜ Pending | ⬜ | Use DI, no hard-coded paths |
| Migrate retry feature to use new libraries | ⬜ Pending | ⬜ | Use DI, no hard-coded paths |
| Update middleware to use new libraries | ⬜ Pending | ⬜ | Use DI throughout |
| Integration tests: features work with new libraries | ⬜ Pending | ⬜ | Test end-to-end |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/5 (0%)

---

### Phase 1 Summary

| Category | Tasks | Completed | Pending | Completion |
|----------|-------|-----------|---------|------------|
| Observability Library | 10 | 0 | 10 | 0% |
| Policy Library | 9 | 0 | 9 | 0% |
| Prompt Library | 9 | 0 | 9 | 0% |
| Feature Migration | 5 | 0 | 5 | 0% |
| **Total** | **33** | **0** | **33** | **0%** |

---

## Phase 2: Remaining Features (Post 2-Week Sprint)

### 2.1 Token/Cost Tracking Verification

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Verify `llm_cost_tracker.py` is used | ⬜ Pending | ⬜ | Check integration |
| Ensure token counting works correctly | ⬜ Pending | ⬜ | Test accuracy |
| Add cost metrics to observability | ⬜ Pending | ⬜ | Integrate with metrics |
| Create cost dashboard/viewer | ⬜ Pending | ⬜ | CLI or web viewer |
| Document cost tracking usage | ⬜ Pending | ⬜ | Documentation |
| Unit tests: token counting | ⬜ Pending | ⬜ | Test accuracy |
| Integration tests: cost tracking in workflow | ⬜ Pending | ⬜ | Test end-to-end |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/8 (0%)

---

### 2.2 Response Caching

| Task | Status | Tests | Notes |
|------|--------|-------|-------|
| Implement cache layer (Redis or in-memory) | ⬜ Pending | ⬜ | Choose implementation |
| Create cache key based on input hash | ⬜ Pending | ⬜ | Hash function |
| Add configurable TTL per agent/query type | ⬜ Pending | ⬜ | Configuration |
| Add cache hit/miss metrics | ⬜ Pending | ⬜ | Metrics collection |
| Implement cache invalidation on prompt updates | ⬜ Pending | ⬜ | Invalidation logic |
| Unit tests: cache behavior | ⬜ Pending | ⬜ | Test cache logic |
| Integration tests: caching in workflow | ⬜ Pending | ⬜ | Test end-to-end |
| All existing tests pass | ⬜ Pending | ⬜ | Verify no regressions |

**Completion**: 0/8 (0%)

---

### Phase 2 Summary

| Category | Tasks | Completed | Pending | Completion |
|----------|-------|-----------|---------|------------|
| Cost Tracking | 8 | 0 | 8 | 0% |
| Response Caching | 8 | 0 | 8 | 0% |
| **Total** | **16** | **0** | **16** | **0%** |

---

## Overall Progress

| Phase | Total Tasks | Completed | Pending | Completion |
|-------|-------------|-----------|---------|------------|
| **Phase 0** (Weeks 1-2) | 43 | 0 | 43 | 0% |
| **Phase 1** (Weeks 3-6) | 33 | 0 | 33 | 0% |
| **Phase 2** (Weeks 7+) | 16 | 0 | 16 | 0% |
| **TOTAL** | **92** | **0** | **92** | **0%** |

---

## Status Legend

- ⬜ **Pending** - Not started
- 🟡 **In Progress** - Currently working on
- ✅ **Completed** - Done and tested
- ❌ **Blocked** - Cannot proceed (document reason)
- ⚠️ **Needs Review** - Ready for your review

---

## Testing Requirements

**Every task must have**:
1. ✅ Unit tests (if applicable)
2. ✅ Integration tests (if applicable)
3. ✅ All existing tests pass (no regressions)
4. ✅ Code review ready (documented, tested)

**No task is considered complete until all tests pass.**

---

## Notes

- **Project Name**: `agent-observable` (micro-library approach)
- **2-Week Target**: Phase 0 complete (working baseline for socialization)
  - Week 1: Foundation (Interfaces, DI, Remove Hard-Coded Paths)
  - Week 2: Critical Features (Timeouts, Retry Logic)
- **Post 2-Week**: Phase 1 (Extract micro-libraries as `agent-observable-*` packages) and Phase 2 (Remaining Features)
- **Micro-Libraries**: Will extract as separate packages:
  - `agent-observable-core/` - Observability
  - `agent-observable-policy/` - Policy decisions
  - `agent-observable-guardrails/` - Guardrails
  - `agent-observable-prompts/` - Prompt management
- **Iterative**: Complete tasks methodically, test thoroughly, review before proceeding
- **No Excuses**: Every change must have solid testing before review
- **Direct Iteration**: Work through tasks quickly, update tracker as we go

---

## 2-Week Sprint Summary

**Total Tasks in 2 Weeks**: 43 tasks
- Foundation: 23 tasks
- Critical Features: 20 tasks

**Success Criteria**:
- ✅ All 43 tasks completed and tested
- ✅ Working baseline with timeouts and retry logic
- ✅ Ready for socialization demo
- ✅ All existing tests pass (no regressions)

---

*This tracker will be updated in real-time as we iterate through implementation.*
