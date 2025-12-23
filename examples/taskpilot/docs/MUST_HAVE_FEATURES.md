# Must-Have Features for Enterprise Shared Library

**Status as of v0.01 (`agent-observable`)**
- **Scope**: This document captures the **capability analysis and prioritization**; the **authoritative implementation status** is tracked in `IMPLEMENTATION_TRACKER.md`.
- **Architecture**: Micro-library + monorepo (`agent-observable`) with `taskpilot` as an example client.
- **Decisions**: Rate limiting is handled by **cloud infrastructure** (Azure APIM / AWS API Gateway); application-level work focuses on timeouts, retries, cost tracking, caching, context management, API rate limit handling, and exception hierarchy.

## Summary from Capability Matrix & Best Practices

Based on analysis of `CAPABILITIES_MATRIX.md` and `MICROSOFT_AGENT_FRAMEWORK_BEST_PRACTICES.md`:

**Current Overall Score**: 65% (48/74 capabilities)

**Critical Gaps Identified**:
- Security: 46% (rate limiting now via infrastructure, timeouts still needed)
- Cost Optimization: 25-38% (token tracking needs verification)
- Operational Excellence: 36% (missing retries, API rate limit handling)

---

## Critical Priority Features (Must Have)

**Note**: Rate limiting handled by cloud infrastructure (Azure APIM / AWS API Gateway) - no custom implementation needed.

### 1. Rate Limiting ⚠️ **CRITICAL**

**Status**: ❌ Not Implemented

**Why Critical**:
- No protection against abuse, DoS attacks
- No API rate limit protection
- Security risk

**Requirements**:
- [ ] Per-user rate limiting (requests per minute)
- [ ] Per-tool rate limiting (tool calls per minute)
- [ ] Global rate limiting (total requests per minute)
- [ ] API rate limit detection and handling
- [ ] Rate limit metrics and alerts
- [ ] Rate limit violations logged as policy decisions

**Integration Points**:
- Middleware (agent calls)
- Tool execution (tool calls)
- LLM client calls (API rate limits)

**Priority**: **P0 - Blocking for production**

---

### 2. Tool Execution Timeouts ⚠️ **CRITICAL** (P0)

**Status**: ✅ **WILL IMPLEMENT** - Planned for Phase 2, Week 7

**Why Critical**:
- Tools can hang indefinitely
- Blocks workflows
- Reliability risk

**Requirements**:
- [ ] Configurable timeout per tool (default: 30s)
- [ ] `asyncio.wait_for` wrapper
- [ ] Timeout events logged as policy decisions
- [ ] Timeout metrics
- [ ] Graceful timeout handling (don't crash workflow)

**Integration Points**:
- `src/core/tool_executor.py`
- Tool execution middleware

**Priority**: **P0 - Blocking for production**

---

### 3. Retry Logic with Exponential Backoff ⚠️ **CRITICAL**

**Status**: ✅ **WILL IMPLEMENT** - Planned for Phase 2, Week 8

**Why Critical**:
- Transient API failures cause workflow failures
- No automatic recovery
- Reliability risk

**Requirements**:
- [ ] Retry decorator with exponential backoff
- [ ] Retry configuration (max attempts, backoff factor)
- [ ] Retry on specific exceptions (API rate limits, timeouts)
- [ ] Retry metrics
- [ ] Integration with LLM client calls

**Integration Points**:
- LLM client calls
- OPA validation calls
- External API calls

**Priority**: **P0 - Blocking for production**

---

### 4. Token/Cost Tracking Verification ⚠️ **CRITICAL** (P0)

**Status**: ⚠️ Partial (code exists, needs verification)

**Why Critical**:
- Cost visibility essential for production
- Optimization opportunities
- Budget management

**Requirements**:
- [ ] Verify `llm_cost_tracker.py` is actually used
- [ ] Ensure token counting works correctly
- [ ] Add cost metrics to observability
- [ ] Create cost dashboard/viewer
- [ ] Document cost tracking usage

**Integration Points**:
- Middleware (after LLM calls)
- Metrics system
- Cost dashboard

**Priority**: **P0 - Blocking for production**

---

## High Priority Features (Should Have)

### 5. Response Caching 🟡 **HIGH**

**Status**: ✅ **WILL IMPLEMENT** - Planned for Phase 2.5 (optional, high value)

**Why Important**:
- Significant cost reduction (30%+)
- Faster responses
- Better user experience

**Requirements**:
- [ ] Cache layer (Redis or in-memory)
- [ ] Cache key based on input hash
- [ ] Configurable TTL per agent/query type
- [ ] Cache hit/miss metrics
- [ ] Invalidate cache on prompt updates

**Priority**: **P1 - High value, not blocking**

---

### 6. Context Window Management 🟡 **HIGH**

**Status**: ❌ Not Implemented

**Why Important**:
- Long conversations exceed context limits
- Need truncation/summarization
- Enables long-running conversations

**Requirements**:
- [ ] Track context window usage per conversation
- [ ] Implement truncation strategy (keep recent, summarize old)
- [ ] Add context summarization (LLM-based)
- [ ] Configurable context limits per agent
- [ ] Add context usage metrics

**Priority**: **P1 - High value, not blocking**

---

### 7. API Rate Limit Handling 🟡 **HIGH**

**Status**: ✅ **WILL IMPLEMENT** - Planned for Phase 2.5 (optional, high value)

**Why Important**:
- OpenAI API rate limits cause failures
- Need intelligent handling
- Improves reliability

**Requirements**:
- [ ] Detect rate limit errors (429 status)
- [ ] Implement exponential backoff on rate limits
- [ ] Add rate limit queue (defer requests)
- [ ] Track rate limit usage per model
- [ ] Alert on approaching rate limits

**Priority**: **P1 - High value, not blocking**

---

## Medium Priority Features (Nice to Have)

### 8. Exception Hierarchy & Error Codes 🟢 **MEDIUM**

**Status**: ✅ **WILL IMPLEMENT** - Planned for future phase (enhancement)

**Why Important**:
- Better debugging
- User experience
- Error tracking

**Requirements**:
- [ ] Create exception hierarchy (BaseAgentException, etc.)
- [ ] Add error code system (e.g., `AGENT_001`, `TOOL_002`)
- [ ] Map error codes to user-friendly messages
- [ ] Include error codes in logs

**Priority**: **P2 - Enhancement**

---

### 9. Advanced Prompt Injection Detection 🟢 **MEDIUM**

**Status**: ⚠️ Basic (NeMo Guardrails provides basic protection)

**Why Important**:
- Security risk mitigation
- Advanced patterns not detected

**Requirements**:
- [ ] Pattern-based injection detection (instruction override, role confusion)
- [ ] Add to middleware before NeMo validation
- [ ] Create `PromptSafetyChecker` class
- [ ] Log detected injection attempts

**Priority**: **P2 - Enhancement**

---

### 10. Input Sanitization 🟢 **MEDIUM**

**Status**: ⚠️ Partial (length limits only)

**Why Important**:
- Prevents encoding-based attacks
- Improves data quality

**Requirements**:
- [ ] Remove control characters from inputs
- [ ] Normalize encoding (UTF-8 validation)
- [ ] Validate character sets
- [ ] Sanitize tool parameters

**Priority**: **P2 - Enhancement**

---

## Integration into Refactoring Plan

### Phase 2: Must-Have Features (Week 7-10)

**All critical features added in this phase**:

1. **Week 7**: Rate Limiting
2. **Week 8**: Tool Execution Timeouts
3. **Week 9**: Retry Logic with Exponential Backoff
4. **Week 10**: Token/Cost Tracking Verification

### Phase 2.5: High Priority Features (Week 11, Optional)

**If time permits**:

5. Response Caching
6. Context Window Management
7. API Rate Limit Handling

### Phase 3+: Medium Priority Features (Future)

**Enhancement phase**:

8. Exception Hierarchy & Error Codes
9. Advanced Prompt Injection Detection
10. Input Sanitization

---

## Feature Dependencies

### Rate Limiting (Infrastructure):
- Configure in Azure APIM / AWS API Gateway
- No application code dependencies
- Metrics available from infrastructure monitoring

### Timeouts Depends On:
- Policy decision logging (for timeout decisions)
- Metrics system (for timeout metrics)

### Retry Logic Depends On:
- Exception handling (to identify retryable exceptions)
- Metrics system (for retry metrics)

### Cost Tracking Depends On:
- LLM client integration (to extract token usage)
- Metrics system (for cost metrics)

---

## Success Metrics

### Rate Limiting
- ✅ Zero rate limit violations in production
- ✅ Rate limit metrics collected
- ✅ Policy decisions logged for violations

### Timeouts
- ✅ Zero hanging operations
- ✅ Timeout metrics collected
- ✅ Policy decisions logged for timeouts

### Retry Logic
- ✅ 95%+ success rate after retries
- ✅ Retry metrics collected
- ✅ Transient failures handled automatically

### Cost Tracking
- ✅ 100% of LLM calls tracked
- ✅ Cost metrics accurate
- ✅ Cost dashboard functional

---

## Conclusion

**Must-Have Features for Enterprise**:
1. ✅ Rate Limiting (Infrastructure - Azure APIM / AWS API Gateway)
2. ✅ Tool Execution Timeouts (Critical - P0) - **WILL IMPLEMENT** (Phase 2, Week 7)
3. ✅ Retry Logic (Critical - P0) - **WILL IMPLEMENT** (Phase 2, Week 8)
4. ✅ Token/Cost Tracking (Critical - P0) - **WILL IMPLEMENT** (Phase 2, Week 9)
5. ✅ Response Caching (High - P1) - **WILL IMPLEMENT** (Phase 2.5, optional)
6. ✅ Context Window Management (High - P1) - **WILL IMPLEMENT** (Phase 2.5, optional)
7. ✅ API Rate Limit Handling (High - P1) - **WILL IMPLEMENT** (Phase 2.5, optional)
8. ✅ Exception Hierarchy & Error Codes (Medium - P2) - **WILL IMPLEMENT** (Future phase)

**These features are integrated into Phase 2 of the refactoring plan and are non-negotiable for enterprise use.**

**Note**: Rate limiting is handled by cloud infrastructure (Azure APIM / AWS API Gateway) to avoid overengineering. This aligns with the principle of addressing real problems that add value, save time, minimize risk, and improve performance & productivity.
