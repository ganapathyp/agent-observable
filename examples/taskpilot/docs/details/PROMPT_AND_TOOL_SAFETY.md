# Prompt & Tool Safety: Best Practices

## Overview

This document covers best practices for ensuring prompt safety (protecting against prompt injection, malicious inputs) and tool safety (validating tool calls, authorization, parameter validation).

## Current Implementation

### Prompt Safety Layers

**1. NeMo Guardrails (LLM I/O Validation)**
- **Location**: `src/core/guardrails/nemo_rails.py`
- **Purpose**: Validates LLM input and output
- **Protection**: Prompt injection, toxic content, PII leakage
- **Implementation**: Integrated in middleware

**2. Input Validation (Middleware)**
- **Location**: `src/core/middleware.py`
- **Purpose**: Validates agent inputs before processing
- **Protection**: Keyword blocking, basic policy enforcement
- **Implementation**: Runs before agent execution

**3. Pydantic Validation**
- **Location**: `src/core/models.py`, `src/core/validation.py`
- **Purpose**: Schema validation for structured data
- **Protection**: Type safety, constraint validation
- **Implementation**: Automatic via Pydantic models

### Tool Safety Layers

**1. Embedded OPA (Policy Enforcement)**
- **Location**: `src/core/guardrails/opa_tool_validator.py`
- **Purpose**: Authorizes tool calls based on policy
- **Protection**: Unauthorized tool calls, parameter validation
- **Implementation**: Validates before tool execution

**2. Tool Parameter Validation**
- **Location**: `src/tools/tools.py`
- **Purpose**: Validates tool parameters
- **Protection**: Invalid parameters, type checking
- **Implementation**: Pydantic models + manual checks

**3. Decision Logging**
- **Location**: `src/core/guardrails/decision_logger.py`
- **Purpose**: Audit trail for all tool calls
- **Protection**: Compliance, forensics
- **Implementation**: Logs all policy decisions

## Best Practices

### Prompt Safety Best Practices

#### 1. Multi-Layer Validation

**Best Practice**: Use multiple layers of validation

```python
# Layer 1: NeMo Guardrails (LLM I/O)
allowed, reason = await guardrails.validate_input(user_input)
if not allowed:
    raise ValueError(f"Input validation failed: {reason}")

# Layer 2: Keyword/Pattern Detection
if contains_suspicious_patterns(user_input):
    raise ValueError("Suspicious input detected")

# Layer 3: Length/Format Validation
if len(user_input) > MAX_INPUT_LENGTH:
    raise ValueError("Input too long")

# Layer 4: Pydantic Schema Validation (for structured inputs)
try:
    validated = InputSchema(**parsed_input)
except ValidationError as e:
    raise ValueError(f"Schema validation failed: {e}")
```

**Current Implementation**: ✅ Multi-layer (NeMo + keyword + Pydantic)

#### 2. Prompt Injection Protection

**Best Practice**: Detect and block prompt injection attempts

**Common Injection Patterns:**
- Instruction override: "Ignore previous instructions..."
- System prompt extraction: "What are your instructions?"
- Role confusion: "You are now a helpful assistant..."
- Encoding tricks: Base64, URL encoding, unicode

**Detection Strategies:**
```python
def detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attempts."""
    injection_patterns = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"forget\s+(everything|all|previous)",
        r"you\s+are\s+now",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"user\s*:\s*",
        r"new\s+instructions?",
        r"override",
    ]
    
    text_lower = text.lower()
    for pattern in injection_patterns:
        if re.search(pattern, text_lower):
            return True
    return False
```

**Current Implementation**: ⚠️ Basic (NeMo Guardrails provides some protection)

#### 3. Input Sanitization

**Best Practice**: Sanitize inputs before processing

```python
def sanitize_input(text: str) -> str:
    """Sanitize user input."""
    # Remove control characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Limit length
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]
    
    return text.strip()
```

**Current Implementation**: ⚠️ Partial (length validation in Pydantic)

#### 4. Rate Limiting

**Best Practice**: Limit request frequency to prevent abuse

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        user_requests = self.requests[user_id]
        
        # Remove old requests
        user_requests[:] = [req_time for req_time in user_requests 
                           if now - req_time < self.window]
        
        if len(user_requests) >= self.max_requests:
            return False
        
        user_requests.append(now)
        return True
```

**Current Implementation**: ❌ Not implemented

#### 5. Content Moderation

**Best Practice**: Filter toxic, harmful, or inappropriate content

```python
def moderate_content(text: str) -> Tuple[bool, str]:
    """Moderate content for toxicity."""
    # Use content moderation API (e.g., OpenAI Moderation API)
    # Or use NeMo Guardrails content filtering
    
    toxic_keywords = ["hate", "violence", "self-harm"]  # Example
    text_lower = text.lower()
    
    for keyword in toxic_keywords:
        if keyword in text_lower:
            return False, f"Content contains inappropriate material: {keyword}"
    
    return True, "Content approved"
```

**Current Implementation**: ⚠️ Basic (NeMo Guardrails, requires full config)

### Tool Safety Best Practices

#### 1. Authorization (Policy-Based)

**Best Practice**: Use policy engine (OPA) for authorization

```python
# Current implementation
allowed, reason, requires_approval = await opa_validator.validate_tool_call(
    tool_name="create_task",
    parameters={"title": title, "priority": priority},
    agent_type="PlannerAgent",
    agent_id="PlannerAgent"
)

if not allowed:
    raise ValueError(f"Tool call denied: {reason}")

if requires_approval:
    # Trigger human approval workflow
    await request_human_approval(tool_call)
```

**Current Implementation**: ✅ Embedded OPA

#### 2. Parameter Validation

**Best Practice**: Validate all tool parameters

```python
# Layer 1: Type validation (Pydantic)
class CreateTaskParams(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    priority: TaskPriority
    description: str = Field(default="", max_length=10000)

# Layer 2: Business logic validation
def validate_task_params(params: CreateTaskParams) -> None:
    if "delete" in params.title.lower():
        raise ValueError("Task title cannot contain 'delete'")
    
    if params.priority == TaskPriority.HIGH and not params.description:
        raise ValueError("High priority tasks require description")

# Layer 3: Policy validation (OPA)
allowed, reason = await opa_validator.validate_tool_call(
    tool_name="create_task",
    parameters=params.dict()
)
```

**Current Implementation**: ✅ Multi-layer (Pydantic + OPA)

#### 3. Tool Call Rate Limiting

**Best Practice**: Limit tool call frequency

```python
class ToolRateLimiter:
    def __init__(self):
        self.call_counts = defaultdict(int)
        self.time_windows = defaultdict(datetime.now)
    
    async def check_rate_limit(self, tool_name: str, max_calls: int = 10) -> bool:
        now = datetime.now()
        window = self.time_windows[tool_name]
        
        if (now - window).seconds > 60:  # Reset window
            self.call_counts[tool_name] = 0
            self.time_windows[tool_name] = now
        
        if self.call_counts[tool_name] >= max_calls:
            return False
        
        self.call_counts[tool_name] += 1
        return True
```

**Current Implementation**: ❌ Not implemented

#### 4. Tool Call Timeout

**Best Practice**: Set timeouts for tool execution

```python
import asyncio

async def execute_tool_with_timeout(tool_func, timeout_seconds: float = 30.0):
    """Execute tool with timeout."""
    try:
        result = await asyncio.wait_for(
            tool_func(),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        raise ValueError(f"Tool execution timed out after {timeout_seconds}s")
```

**Current Implementation**: ❌ Not implemented

#### 5. Tool Call Sandboxing

**Best Practice**: Execute dangerous tools in sandboxed environment

```python
# For tools that modify data or call external systems
def execute_in_sandbox(tool_func, *args, **kwargs):
    """Execute tool in sandboxed environment."""
    # Use container isolation
    # Or use restricted execution context
    # Or use read-only filesystem
    pass
```

**Current Implementation**: ❌ Not implemented (tools execute directly)

#### 6. Tool Call Auditing

**Best Practice**: Log all tool calls for audit

```python
# Current implementation
decision = PolicyDecision.create(
    decision_type=DecisionType.TOOL_CALL,
    result=DecisionResult.ALLOW if allowed else DecisionResult.DENY,
    reason=reason,
    context={
        "tool_name": tool_name,
        "parameters": parameters,
        "agent_type": agent_type,
    },
    tool_name=tool_name,
    agent_id=agent_id,
    latency_ms=latency_ms,
)
await decision_logger.log_decision(decision)
```

**Current Implementation**: ✅ Decision logging

#### 7. Parameter Sanitization

**Best Practice**: Sanitize tool parameters

```python
def sanitize_tool_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize tool parameters."""
    sanitized = {}
    for key, value in params.items():
        if isinstance(value, str):
            # Remove control characters
            value = ''.join(c for c in value if c.isprintable() or c.isspace())
            # Limit length
            value = value[:10000]  # Max length
        sanitized[key] = value
    return sanitized
```

**Current Implementation**: ⚠️ Partial (Pydantic validation)

## Comprehensive Safety Checklist

### Prompt Safety Checklist

- [x] **Multi-layer validation** (NeMo + keyword + Pydantic)
- [x] **Input length limits** (Pydantic max_length)
- [x] **Basic injection detection** (NeMo Guardrails)
- [ ] **Advanced injection patterns** (instruction override, role confusion)
- [ ] **Input sanitization** (control characters, encoding)
- [ ] **Rate limiting** (prevent abuse)
- [ ] **Content moderation** (toxic content filtering)
- [ ] **Input encoding validation** (prevent encoding attacks)
- [ ] **Prompt versioning** (track prompt changes)
- [x] **Audit logging** (decision logs)

### Tool Safety Checklist

- [x] **Policy-based authorization** (Embedded OPA)
- [x] **Parameter validation** (Pydantic models)
- [x] **Type checking** (Pydantic)
- [x] **Decision logging** (audit trail)
- [ ] **Rate limiting** (tool call frequency)
- [ ] **Timeouts** (prevent hanging)
- [ ] **Sandboxing** (isolated execution)
- [ ] **Parameter sanitization** (control characters)
- [ ] **Resource limits** (memory, CPU)
- [ ] **Error handling** (graceful failures)

## Recommended Implementation Priority

### High Priority (Security Critical)

1. **Advanced Prompt Injection Detection**
   - Detect instruction override patterns
   - Detect role confusion attempts
   - Detect encoding tricks

2. **Input Sanitization**
   - Remove control characters
   - Normalize encoding
   - Validate character sets

3. **Rate Limiting**
   - Per-user rate limits
   - Per-tool rate limits
   - Global rate limits

### Medium Priority (Best Practice)

4. **Content Moderation**
   - Toxic content filtering
   - PII detection
   - Harmful content detection

5. **Tool Timeouts**
   - Execution time limits
   - Resource limits
   - Graceful timeout handling

6. **Parameter Sanitization**
   - Control character removal
   - Length limits
   - Type coercion

### Low Priority (Nice to Have)

7. **Sandboxing**
   - Container isolation
   - Restricted execution
   - Read-only filesystem

8. **Advanced Monitoring**
   - Anomaly detection
   - Pattern recognition
   - Automated alerting

## Implementation Examples

### Enhanced Prompt Injection Detection

```python
# src/core/guardrails/prompt_safety.py
import re
from typing import List, Tuple

class PromptSafetyChecker:
    """Advanced prompt injection detection."""
    
    INJECTION_PATTERNS = [
        # Instruction override
        (r"ignore\s+(previous|all|above|earlier)\s+instructions?", "instruction_override"),
        (r"forget\s+(everything|all|previous|what)", "instruction_override"),
        (r"disregard\s+(previous|all|above)", "instruction_override"),
        
        # Role confusion
        (r"you\s+are\s+now\s+(a|an)\s+", "role_confusion"),
        (r"pretend\s+you\s+are", "role_confusion"),
        (r"act\s+as\s+if\s+you\s+are", "role_confusion"),
        
        # System prompt extraction
        (r"what\s+are\s+your\s+instructions?", "prompt_extraction"),
        (r"show\s+me\s+your\s+system\s+prompt", "prompt_extraction"),
        (r"repeat\s+your\s+instructions", "prompt_extraction"),
        
        # Encoding tricks
        (r"base64|url\s+encode|decode", "encoding_trick"),
        
        # New instructions
        (r"new\s+instructions?:", "new_instructions"),
        (r"updated\s+instructions?:", "new_instructions"),
    ]
    
    def check_prompt_injection(self, text: str) -> Tuple[bool, List[str]]:
        """Check for prompt injection attempts.
        
        Returns:
            (is_safe, detected_patterns)
        """
        detected = []
        text_lower = text.lower()
        
        for pattern, pattern_type in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected.append(pattern_type)
        
        return len(detected) == 0, detected
```

### Enhanced Tool Safety

```python
# src/core/guardrails/tool_safety.py
import asyncio
from typing import Dict, Any, Callable
from datetime import datetime, timedelta

class ToolSafetyManager:
    """Comprehensive tool safety management."""
    
    def __init__(self):
        self.rate_limiter = ToolRateLimiter()
        self.timeout_seconds = 30.0
    
    async def validate_and_execute(
        self,
        tool_func: Callable,
        tool_name: str,
        parameters: Dict[str, Any],
        agent_id: str
    ) -> Any:
        """Validate and execute tool with safety checks."""
        
        # 1. Rate limiting
        if not await self.rate_limiter.check_rate_limit(tool_name):
            raise ValueError(f"Rate limit exceeded for {tool_name}")
        
        # 2. Parameter sanitization
        sanitized_params = self.sanitize_parameters(parameters)
        
        # 3. OPA validation
        from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator
        opa_validator = OPAToolValidator(use_embedded=True)
        allowed, reason, requires_approval = await opa_validator.validate_tool_call(
            tool_name=tool_name,
            parameters=sanitized_params,
            agent_type=agent_id,
            agent_id=agent_id
        )
        
        if not allowed:
            raise ValueError(f"Tool call denied: {reason}")
        
        if requires_approval:
            # Trigger approval workflow
            await self.request_approval(tool_name, sanitized_params)
        
        # 4. Execute with timeout
        try:
            result = await asyncio.wait_for(
                tool_func(**sanitized_params),
                timeout=self.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            raise ValueError(f"Tool {tool_name} execution timed out")
    
    def sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize tool parameters."""
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Remove control characters
                value = ''.join(c for c in value if c.isprintable() or c.isspace())
                # Limit length
                value = value[:10000]
            sanitized[key] = value
        return sanitized
```

## Comparison: Current vs. Best Practice

| Safety Feature | Current | Best Practice | Priority |
|----------------|---------|---------------|----------|
| **Prompt Injection Detection** | ⚠️ Basic (NeMo) | ✅ Advanced patterns | High |
| **Input Sanitization** | ⚠️ Partial | ✅ Comprehensive | High |
| **Rate Limiting** | ❌ None | ✅ Per-user/tool | High |
| **Content Moderation** | ⚠️ Basic (NeMo) | ✅ Full moderation | Medium |
| **Tool Authorization** | ✅ OPA | ✅ OPA + RBAC | Good |
| **Parameter Validation** | ✅ Pydantic + OPA | ✅ Multi-layer | Good |
| **Tool Timeouts** | ❌ None | ✅ Configurable | Medium |
| **Tool Sandboxing** | ❌ None | ✅ Isolated execution | Low |
| **Audit Logging** | ✅ Decision logs | ✅ Comprehensive | Good |

## Recommendations

### Immediate Actions

1. **Add advanced prompt injection detection**
   - Implement pattern matching for common injection attempts
   - Add to middleware before NeMo validation

2. **Implement input sanitization**
   - Remove control characters
   - Normalize encoding
   - Validate character sets

3. **Add rate limiting**
   - Per-user limits
   - Per-tool limits
   - Global limits

### Short-Term Improvements

4. **Enhance content moderation**
   - Integrate OpenAI Moderation API
   - Or enhance NeMo Guardrails config

5. **Add tool timeouts**
   - Configurable per-tool timeouts
   - Graceful timeout handling

6. **Improve parameter sanitization**
   - Comprehensive sanitization
   - Type coercion
   - Length limits

### Long-Term Enhancements

7. **Tool sandboxing**
   - Container-based isolation
   - Restricted execution context

8. **Advanced monitoring**
   - Anomaly detection
   - Automated alerting
   - Pattern recognition

## Summary

**Current State**: Good foundation with multi-layer validation (NeMo + OPA + Pydantic)

**Strengths**:
- ✅ Multi-layer prompt validation
- ✅ Policy-based tool authorization
- ✅ Comprehensive audit logging
- ✅ Parameter type validation

**Gaps**:
- ⚠️ Advanced prompt injection detection
- ⚠️ Input sanitization
- ❌ Rate limiting
- ❌ Tool timeouts
- ❌ Content moderation (full)

**Priority**: Focus on prompt injection detection and rate limiting for immediate security improvements.
