# Production Guardrails Architecture - Minimum Viable Implementation

## Executive Summary

This document outlines the **minimum viable production guardrails** architecture for TaskPilot, covering:
1. **NeMo Guardrails** for LLM input/output validation
2. **OPA embedded** for agent tool call validation
3. **Envoy + OPA** at API ingress for request-level policies
4. **Decision logging** for audit and compliance
5. **Human approval paths** modeled in policy

**Status**: Architecture design - no code changes made

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Ingress Layer                        │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│  │  Envoy   │────────▶│   OPA    │────────▶│ Decision │       │
│  │ Gateway  │         │  Server  │         │  Logger  │       │
│  └────┬─────┘         └──────────┘         └──────────┘       │
│       │                                                         │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Input/Output Layer                       │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │ NeMo         │         │ Decision     │                     │
│  │ Guardrails   │────────▶│ Logger       │                     │
│  │ (I/O Rails)  │         │              │                     │
│  └──────┬───────┘         └──────────────┘                     │
└─────────┼───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Tool Call Layer                       │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│  │  Agent   │────────▶│   OPA    │────────▶│ Decision │       │
│  │  Tool    │         │ Embedded │         │  Logger  │       │
│  │  Call    │         │  Policy  │         │          │       │
│  └────┬─────┘         └──────────┘         └──────────┘       │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐                                                  │
│  │ Human    │  (If policy requires approval)                   │
│  │ Approval │                                                  │
│  └──────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. NeMo Guardrails (LLM I/O Validation)

### Purpose
Validate and sanitize LLM inputs and outputs to prevent:
- Prompt injection attacks
- Toxic/harmful content
- Data leakage
- Off-topic responses
- Jailbreak attempts

### Current State

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Input Validation** | ❌ Not implemented | No LLM input validation |
| **Output Validation** | ❌ Not implemented | No LLM output validation |
| **Content Moderation** | ❌ Not implemented | No content filtering |
| **Prompt Injection Protection** | ❌ Not implemented | No injection detection |
| **Streaming Validation** | ❌ Not implemented | No streaming support |

### Recommended Architecture

**Integration Point**: Middleware layer (before/after agent execution)

```
User Input
    │
    ▼
┌─────────────────┐
│ NeMo Guardrails │  ← Input Rails
│  Input Rails   │     - Prompt injection detection
│                 │     - Content moderation
│                 │     - Topic validation
└────────┬────────┘
         │
         ▼
    Agent Execution
         │
         ▼
┌─────────────────┐
│ NeMo Guardrails │  ← Output Rails
│  Output Rails   │     - Response validation
│                 │     - Sensitive data detection
│                 │     - Topic adherence
└────────┬────────┘
         │
         ▼
    Validated Output
```

### Implementation Strategy

**Phase 1: Basic Input/Output Rails**
```python
# src/core/guardrails/nemo_rails.py
from nemoguardrails import LLMRails, RailsConfig

class NeMoGuardrailsWrapper:
    """Wrapper for NeMo Guardrails integration."""
    
    def __init__(self, config_path: Path):
        self.config = RailsConfig.from_path(config_path)
        self.rails = LLMRails(config=self.config)
    
    async def validate_input(self, input_text: str, user_id: str = None) -> tuple[bool, str]:
        """Validate LLM input.
        
        Returns:
            (allowed, reason)
        """
        result = await self.rails.validate_input(
            input_text=input_text,
            user_id=user_id
        )
        return result.allowed, result.reason
    
    async def validate_output(self, output_text: str, context: dict = None) -> tuple[bool, str]:
        """Validate LLM output.
        
        Returns:
            (allowed, reason)
        """
        result = await self.rails.validate_output(
            output_text=output_text,
            context=context
        )
        return result.allowed, result.reason
```

**Configuration Example** (`guardrails/config.yml`):
```yaml
rails:
  input:
    flows:
      - self_check_input
      - check_jailbreak
      - check_pii
    models:
      - type: moderation
        provider: openai
        model: moderation-latest
  
  output:
    flows:
      - self_check_output
      - check_factual_consistency
      - check_pii
    models:
      - type: moderation
        provider: openai
        model: moderation-latest

models:
  - type: main
    provider: openai
    model: gpt-4o-mini
```

### Integration with Middleware

```python
# src/core/middleware.py (enhanced)
from taskpilot.core.guardrails.nemo_rails import NeMoGuardrailsWrapper

async def audit_and_policy_with_guardrails(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]]
) -> None:
    """Middleware with NeMo Guardrails."""
    guardrails = get_guardrails_instance()
    
    # Input validation
    input_text = _extract_text_from_messages(context.messages)
    allowed, reason = await guardrails.validate_input(input_text)
    if not allowed:
        logger.error(f"[GUARDRAILS] Input blocked: {reason}")
        raise ValueError(f"Input validation failed: {reason}")
    
    # Execute agent
    await next(context)
    
    # Output validation
    output_text = _extract_text_from_result(context.result)
    allowed, reason = await guardrails.validate_output(output_text)
    if not allowed:
        logger.error(f"[GUARDRAILS] Output blocked: {reason}")
        raise ValueError(f"Output validation failed: {reason}")
    
    # Log decision
    log_guardrails_decision("input", input_text, allowed, reason)
    log_guardrails_decision("output", output_text, allowed, reason)
```

### Best Practices

1. **Input Rails**:
   - Prompt injection detection
   - Content moderation (toxic, harmful)
   - PII detection
   - Topic validation
   - Jailbreak detection

2. **Output Rails**:
   - Response quality checks
   - Factual consistency
   - PII leakage prevention
   - Topic adherence
   - Hallucination detection

3. **Streaming Support**:
   - Validate chunks incrementally
   - Block early if violation detected
   - Reduce latency with chunk validation

---

## 2. OPA Embedded for Agent Tool Calls

### Purpose
Validate agent tool calls before execution to ensure:
- Authorized tool usage
- Valid parameters
- Compliance with policies
- Resource access control

### Current State

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Tool Call Validation** | ❌ Not implemented | No validation before tool execution |
| **OPA Integration** | ❌ Not implemented | No OPA for tool calls |
| **Parameter Validation** | ⚠️ Basic | Pydantic validation only |
| **Authorization** | ❌ Not implemented | No role-based tool access |
| **Policy Enforcement** | ❌ Not implemented | No policy-driven tool blocking |

### Recommended Architecture

**Integration Point**: Tool execution layer (before `@ai_function` execution)

```
Agent decides to call tool
    │
    ▼
┌─────────────────┐
│  Tool Call      │
│  Interceptor    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OPA Embedded   │  ← Policy evaluation
│  Policy Engine  │     - Tool authorization
│                 │     - Parameter validation
│                 │     - Resource access control
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
 Allow    Deny
    │         │
    │         └──► Log & Raise Error
    │
    ▼
┌─────────────────┐
│  Tool Execution │
└─────────────────┘
```

### Implementation Strategy

**OPA Policy for Tool Calls** (`policies/tool_calls.rego`):
```rego
package taskpilot.tool_calls

import future.keywords.if

default allow = false

# Allow create_task tool
allow if {
    input.tool_name == "create_task"
    input.agent_type == "PlannerAgent"
    validate_task_params(input.parameters)
}

# Allow notify_external_system with restrictions
allow if {
    input.tool_name == "notify_external_system"
    input.agent_type in ["ExecutorAgent", "ReviewerAgent"]
    not contains(input.parameters.message, "delete")
}

# Block dangerous tool calls
deny[msg] if {
    input.tool_name == "delete_task"
    msg := "delete_task tool is not authorized"
}

# Require human approval for high-risk operations
require_approval if {
    input.tool_name == "create_task"
    input.parameters.priority == "high"
    input.parameters.title = contains(input.parameters.title, "sensitive")
}

# Validate task parameters
validate_task_params(params) if {
    params.title != ""
    count(params.title) <= 500
    params.priority in ["high", "medium", "low"]
}
```

**Python Integration**:
```python
# src/core/guardrails/opa_tool_validator.py
import opa_client

class OPAToolValidator:
    """OPA-based tool call validator."""
    
    def __init__(self, opa_url: str = "http://localhost:8181"):
        self.opa_url = opa_url
        self.client = opa_client.Client(base_url=opa_url)
    
    async def validate_tool_call(
        self,
        tool_name: str,
        parameters: dict,
        agent_type: str,
        agent_id: str = None
    ) -> tuple[bool, str, bool]:
        """Validate tool call using OPA.
        
        Returns:
            (allowed, reason, requires_approval)
        """
        input_data = {
            "tool_name": tool_name,
            "parameters": parameters,
            "agent_type": agent_type,
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = await self.client.check_policy(
            package="taskpilot.tool_calls",
            input=input_data
        )
        
        allowed = result.get("result", {}).get("allow", False)
        deny_reasons = result.get("result", {}).get("deny", [])
        requires_approval = result.get("result", {}).get("require_approval", False)
        
        reason = deny_reasons[0] if deny_reasons else ("Allowed" if allowed else "Denied")
        
        return allowed, reason, requires_approval
```

**Tool Decorator Enhancement**:
```python
# src/tools/tools.py (enhanced)
from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator

tool_validator = OPAToolValidator()

def validate_tool_call(func):
    """Decorator to validate tool calls with OPA."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract tool name and parameters
        tool_name = func.__name__
        parameters = kwargs
        
        # Get agent context (from middleware or context)
        agent_type = get_current_agent_type()
        agent_id = get_current_agent_id()
        
        # Validate with OPA
        allowed, reason, requires_approval = await tool_validator.validate_tool_call(
            tool_name=tool_name,
            parameters=parameters,
            agent_type=agent_type,
            agent_id=agent_id
        )
        
        # Log decision
        log_tool_call_decision(tool_name, allowed, reason, requires_approval)
        
        # Check if approval required
        if requires_approval:
            # Route to human approval workflow
            approval_id = await request_human_approval(tool_name, parameters)
            if not await check_approval_status(approval_id):
                raise ValueError(f"Tool call requires approval: {approval_id}")
        
        if not allowed:
            raise ValueError(f"Tool call denied: {reason}")
        
        # Execute tool
        return await func(*args, **kwargs)
    
    return wrapper

@ai_function
@validate_tool_call
async def create_task(title: str, priority: str) -> str:
    """Create a task with title and priority."""
    # ... existing implementation
```

### Best Practices

1. **Policy Structure**:
   - Separate policies per tool type
   - Environment-specific rules
   - Agent-type-based authorization
   - Parameter validation rules

2. **Performance**:
   - Cache policy decisions (with TTL)
   - Use OPA bundles (pre-compiled)
   - Local OPA server (embedded) for low latency

3. **Testing**:
   - Unit tests for policies
   - Integration tests for tool validation
   - Policy regression tests

---

## 3. Envoy + OPA at API Ingress

### Purpose
Enforce policies at the API gateway level before requests reach the application:
- Request authentication/authorization
- Rate limiting
- IP whitelisting/blacklisting
- Request validation
- API versioning

### Current State

| Component | Status | Implementation |
|-----------|--------|----------------|
| **API Gateway** | ❌ Not implemented | No gateway layer |
| **Envoy Integration** | ❌ Not implemented | No Envoy proxy |
| **Ingress Policies** | ❌ Not implemented | No request-level policies |
| **Rate Limiting** | ❌ Not implemented | No rate limits |
| **Authentication** | ❌ Not implemented | No auth at ingress |

### Recommended Architecture

```
Client Request
    │
    ▼
┌─────────────┐
│   Envoy     │  ← API Gateway
│   Proxy     │     - Load balancing
│             │     - TLS termination
│             │     - Request routing
└──────┬──────┘
       │
       │ External Auth Request
       ▼
┌─────────────┐
│ OPA-Envoy   │  ← Policy evaluation
│   Plugin    │     - Authorization
│             │     - Rate limiting
│             │     - Request validation
└──────┬──────┘
       │
       │ Allow/Deny
       ▼
┌─────────────┐
│  Decision   │
│   Logger    │
└─────────────┘
       │
       │ (if allowed)
       ▼
┌─────────────┐
│  TaskPilot  │
│  Backend    │
└─────────────┘
```

### Implementation Strategy

**Envoy Configuration** (`envoy.yaml`):
```yaml
listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
      - filters:
          - name: envoy.filters.network.http_connection_manager
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
              stat_prefix: ingress_http
              route_config:
                name: local_route
                virtual_hosts:
                  - name: local_service
                    domains: ["*"]
                    routes:
                      - match:
                          prefix: "/"
                        route:
                          cluster: taskpilot_backend
              http_filters:
                - name: envoy.filters.http.ext_authz
                  typed_config:
                    "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
                    transport_api_version: V3
                    with_request_body:
                      max_request_bytes: 8192
                    failure_mode_allow: false
                    grpc_service:
                      google_grpc:
                        target_uri: 127.0.0.1:9191
                        stat_prefix: ext_authz
                - name: envoy.filters.http.router
                  typed_config:
                    "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

clusters:
  - name: taskpilot_backend
    connect_timeout: 30s
    type: LOGICAL_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: taskpilot_backend
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: taskpilot
                    port_value: 8000
```

**OPA Policy for Ingress** (`policies/ingress.rego`):
```rego
package taskpilot.ingress

import future.keywords.if

default allow = false

# Allow authenticated requests
allow if {
    input.parsed_path[0] == "api"
    input.parsed_path[1] == "v1"
    authenticated_user(input.headers)
    rate_limit_ok(input.headers["user-id"])
}

# Block unauthenticated requests
deny[msg] if {
    not authenticated_user(input.headers)
    msg := "Authentication required"
}

# Rate limiting
deny[msg] if {
    user_id := input.headers["user-id"]
    rate_limit_exceeded(user_id)
    msg := "Rate limit exceeded"
}

# IP whitelisting (production)
deny[msg] if {
    input.attributes.source.address.socket_address.address not in data.allowed_ips
    input.environment == "production"
    msg := "IP address not whitelisted"
}

# Authenticated user check
authenticated_user(headers) if {
    headers["authorization"] != ""
    # Validate JWT token (simplified)
}

# Rate limit check
rate_limit_ok(user_id) if {
    # Check rate limit from cache/Redis
    # Implementation depends on rate limiter
}
```

**OPA-Envoy Plugin Setup**:
```bash
# Deploy OPA-Envoy plugin
opa run --server \
  --config-file=opa-config.yaml \
  --set=plugins.envoy_ext_authz_grpc.addr=:9191 \
  --set=plugins.envoy_ext_authz_grpc.enable_reflection=true \
  policies/
```

### Best Practices

1. **Policy Structure**:
   - Separate ingress policies from application policies
   - Environment-specific rules (dev/staging/prod)
   - IP whitelisting for production
   - Rate limiting per user/IP

2. **Performance**:
   - OPA as sidecar (low latency)
   - Policy caching
   - Async policy evaluation

3. **Security**:
   - TLS termination at Envoy
   - JWT validation
   - Request size limits
   - Timeout protection

---

## 4. Decision Logging

### Purpose
Log all policy decisions for:
- Audit trails
- Compliance
- Debugging
- Analytics
- Policy optimization

### Current State

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Policy Decision Logging** | ❌ Not implemented | No structured decision logs |
| **Audit Trail** | ⚠️ Basic | Simple INFO logs |
| **Decision Storage** | ❌ Not implemented | No persistent decision store |
| **Query Interface** | ❌ Not implemented | No way to query decisions |
| **Compliance Reports** | ❌ Not implemented | No compliance reporting |

### Recommended Architecture

```
Policy Decision
    │
    ▼
┌─────────────────┐
│ Decision Logger │  ← Centralized logging
│                 │     - Structured format
│                 │     - Async writes
│                 │     - Batching
└────────┬────────┘
         │
    ┌────┴────┐
    │        │
    ▼        ▼
┌────────┐ ┌──────────┐
│  File  │ │  Database │  ← Persistent storage
│  Logs  │ │  (Postgres)│     - Queryable
└────────┘ └──────────┘
    │        │
    └────┬───┘
         │
         ▼
┌─────────────────┐
│  Analytics      │  ← Decision analysis
│  Dashboard      │     - Policy effectiveness
│                 │     - Compliance reports
└─────────────────┘
```

### Implementation Strategy

**Decision Log Schema**:
```python
# src/core/guardrails/decision_log.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class DecisionType(str, Enum):
    GUARDRAILS_INPUT = "guardrails_input"
    GUARDRAILS_OUTPUT = "guardrails_output"
    TOOL_CALL = "tool_call"
    INGRESS = "ingress"
    HUMAN_APPROVAL = "human_approval"

class DecisionResult(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"

@dataclass
class PolicyDecision:
    """Structured policy decision log entry."""
    decision_id: str
    timestamp: datetime
    decision_type: DecisionType
    result: DecisionResult
    reason: str
    context: Dict[str, Any]
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    policy_version: Optional[str] = None
    latency_ms: Optional[float] = None
```

**Decision Logger**:
```python
# src/core/guardrails/decision_logger.py
import json
import asyncio
from pathlib import Path
from typing import List
from datetime import datetime

class DecisionLogger:
    """Centralized decision logging."""
    
    def __init__(
        self,
        log_file: Path = None,
        db_url: str = None,
        batch_size: int = 100,
        flush_interval: float = 5.0
    ):
        self.log_file = log_file
        self.db_url = db_url
        self.batch: List[PolicyDecision] = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._flush_task = None
    
    async def log_decision(self, decision: PolicyDecision):
        """Log a policy decision."""
        self.batch.append(decision)
        
        if len(self.batch) >= self.batch_size:
            await self.flush()
    
    async def flush(self):
        """Flush batched decisions."""
        if not self.batch:
            return
        
        # Write to file
        if self.log_file:
            await self._write_to_file(self.batch)
        
        # Write to database
        if self.db_url:
            await self._write_to_db(self.batch)
        
        self.batch.clear()
    
    async def _write_to_file(self, decisions: List[PolicyDecision]):
        """Write decisions to file (JSONL format)."""
        with open(self.log_file, 'a') as f:
            for decision in decisions:
                f.write(json.dumps(decision.__dict__, default=str) + '\n')
    
    async def _write_to_db(self, decisions: List[PolicyDecision]):
        """Write decisions to database."""
        # Implementation depends on database choice
        # Example: PostgreSQL with async driver
        pass
```

**Integration Points**:
```python
# Log NeMo Guardrails decisions
async def log_guardrails_decision(
    decision_type: str,
    content: str,
    allowed: bool,
    reason: str
):
    decision = PolicyDecision(
        decision_id=generate_id(),
        timestamp=datetime.utcnow(),
        decision_type=DecisionType.GUARDRAILS_INPUT if decision_type == "input" else DecisionType.GUARDRAILS_OUTPUT,
        result=DecisionResult.ALLOW if allowed else DecisionResult.DENY,
        reason=reason,
        context={"content": content[:1000]}  # Truncate for storage
    )
    await decision_logger.log_decision(decision)

# Log tool call decisions
async def log_tool_call_decision(
    tool_name: str,
    allowed: bool,
    reason: str,
    requires_approval: bool
):
    decision = PolicyDecision(
        decision_id=generate_id(),
        timestamp=datetime.utcnow(),
        decision_type=DecisionType.TOOL_CALL,
        result=DecisionResult.REQUIRE_APPROVAL if requires_approval else (DecisionResult.ALLOW if allowed else DecisionResult.DENY),
        reason=reason,
        context={"tool_name": tool_name},
        tool_name=tool_name
    )
    await decision_logger.log_decision(decision)
```

### Best Practices

1. **Log Format**:
   - Structured JSON (JSONL for files)
   - Include all context
   - Truncate large content
   - Include policy version

2. **Performance**:
   - Async logging
   - Batching
   - Non-blocking writes
   - Separate logging thread/process

3. **Storage**:
   - File logs for local dev
   - Database for production (queryable)
   - Retention policies
   - Archival for compliance

---

## 5. Human Approval Paths Modeled in Policy

### Purpose
Define human-in-the-loop workflows in policy:
- When approval is required
- Who can approve
- Approval workflows
- Timeout handling

### Current State

| Component | Status | Implementation |
|-----------|--------|----------------|
| **Human Approval** | ✅ Implemented | Review workflow exists |
| **Policy-Driven** | ❌ Not implemented | Hard-coded in code |
| **Approval Rules** | ❌ Not implemented | No policy for when approval needed |
| **Approval Routing** | ❌ Not implemented | No role-based routing |
| **Timeout Handling** | ❌ Not implemented | No approval timeouts |

### Recommended Architecture

**OPA Policy for Human Approval** (`policies/approval.rego`):
```rego
package taskpilot.approval

import future.keywords.if

# Determine if human approval is required
require_approval if {
    input.tool_name == "create_task"
    input.parameters.priority == "high"
}

require_approval if {
    input.tool_name == "create_task"
    contains(input.parameters.title, "sensitive")
}

require_approval if {
    input.tool_name == "create_task"
    input.parameters.priority == "high"
    input.environment == "production"
}

# Determine who can approve
approver_roles[role] if {
    require_approval
    input.parameters.priority == "high"
    role := "admin"
}

approver_roles[role] if {
    require_approval
    input.parameters.priority == "medium"
    role := "manager"
}

# Approval timeout (hours)
approval_timeout if {
    require_approval
    input.parameters.priority == "high"
    timeout := 24  # 24 hours for high priority
}

approval_timeout if {
    require_approval
    input.parameters.priority == "medium"
    timeout := 48  # 48 hours for medium priority
}

# Auto-reject if timeout
auto_reject_on_timeout if {
    require_approval
    input.parameters.priority == "high"
}
```

**Approval Workflow Integration**:
```python
# src/core/guardrails/approval_workflow.py
from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator

class ApprovalWorkflow:
    """Policy-driven human approval workflow."""
    
    def __init__(self, opa_validator: OPAToolValidator):
        self.opa_validator = opa_validator
        self.task_store = get_task_store()
    
    async def check_approval_required(
        self,
        tool_name: str,
        parameters: dict,
        agent_type: str
    ) -> tuple[bool, dict]:
        """Check if approval is required using OPA policy.
        
        Returns:
            (requires_approval, approval_metadata)
        """
        result = await self.opa_validator.validate_tool_call(
            tool_name=tool_name,
            parameters=parameters,
            agent_type=agent_type
        )
        
        allowed, reason, requires_approval = result
        
        if requires_approval:
            # Get approval metadata from OPA
            approval_metadata = await self._get_approval_metadata(
                tool_name, parameters, agent_type
            )
            return True, approval_metadata
        
        return False, {}
    
    async def _get_approval_metadata(
        self,
        tool_name: str,
        parameters: dict,
        agent_type: str
    ) -> dict:
        """Get approval metadata from OPA policy."""
        input_data = {
            "tool_name": tool_name,
            "parameters": parameters,
            "agent_type": agent_type
        }
        
        result = await self.opa_validator.client.check_policy(
            package="taskpilot.approval",
            input=input_data
        )
        
        return {
            "approver_roles": result.get("result", {}).get("approver_roles", []),
            "timeout_hours": result.get("result", {}).get("approval_timeout", 48),
            "auto_reject": result.get("result", {}).get("auto_reject_on_timeout", False)
        }
    
    async def request_approval(
        self,
        tool_name: str,
        parameters: dict,
        approval_metadata: dict
    ) -> str:
        """Request human approval and return approval ID."""
        # Create approval request in task store
        approval_id = generate_id()
        
        # Store approval request
        await self.task_store.create_approval_request(
            approval_id=approval_id,
            tool_name=tool_name,
            parameters=parameters,
            approver_roles=approval_metadata["approver_roles"],
            timeout_hours=approval_metadata["timeout_hours"],
            auto_reject=approval_metadata["auto_reject"]
        )
        
        # Notify approvers (email, Slack, etc.)
        await self._notify_approvers(approval_id, approval_metadata["approver_roles"])
        
        return approval_id
```

**Integration with Tool Calls**:
```python
# Enhanced tool call validation
async def validate_tool_call_with_approval(
    tool_name: str,
    parameters: dict,
    agent_type: str
):
    """Validate tool call with approval workflow."""
    approval_workflow = ApprovalWorkflow(opa_validator)
    
    # Check if approval required
    requires_approval, approval_metadata = await approval_workflow.check_approval_required(
        tool_name, parameters, agent_type
    )
    
    if requires_approval:
        # Request approval
        approval_id = await approval_workflow.request_approval(
            tool_name, parameters, approval_metadata
        )
        
        # Wait for approval (with timeout)
        approved = await approval_workflow.wait_for_approval(
            approval_id,
            timeout_hours=approval_metadata["timeout_hours"]
        )
        
        if not approved:
            raise ValueError(f"Tool call approval denied or timed out: {approval_id}")
        
        # Log approval decision
        await log_approval_decision(approval_id, approved=True)
    
    # Proceed with tool execution
    return True
```

### Best Practices

1. **Policy Structure**:
   - Clear approval criteria
   - Role-based approvers
   - Timeout policies
   - Escalation rules

2. **Workflow**:
   - Async approval requests
   - Notification system
   - Approval tracking
   - Timeout handling

3. **Integration**:
   - Seamless with tool calls
   - Non-blocking where possible
   - Clear approval UI/CLI

---

## Integration Architecture

### Complete Flow

```
1. Client Request
   │
   ▼
2. Envoy Gateway
   │
   ├─► OPA Ingress Policy ──► Decision Logger
   │
   ▼
3. NeMo Guardrails (Input)
   │
   ├─► Decision Logger
   │
   ▼
4. Agent Execution
   │
   ├─► Tool Call
   │   │
   │   ├─► OPA Tool Policy ──► Decision Logger
   │   │
   │   ├─► Requires Approval?
   │   │   │
   │   │   ├─► Yes ──► Human Approval Workflow
   │   │   │           │
   │   │   │           └─► Decision Logger
   │   │   │
   │   │   └─► No ──► Execute Tool
   │   │
   │   └─► Tool Execution
   │
   ▼
5. NeMo Guardrails (Output)
   │
   ├─► Decision Logger
   │
   ▼
6. Response to Client
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. ✅ Decision logging infrastructure
2. ✅ OPA embedded for tool calls
3. ✅ Basic approval workflow

### Phase 2: LLM Guardrails (Week 3-4)
4. ✅ NeMo Guardrails integration
5. ✅ Input/output validation
6. ✅ Decision logging for guardrails

### Phase 3: API Gateway (Week 5-6)
7. ✅ Envoy setup
8. ✅ OPA-Envoy plugin
9. ✅ Ingress policies

### Phase 4: Policy Refinement (Week 7-8)
10. ✅ Policy-driven approval
11. ✅ Advanced approval workflows
12. ✅ Compliance reporting

---

## Dependencies

### Required Packages
```txt
# NeMo Guardrails
nemoguardrails>=0.5.0

# OPA
opa-client>=0.1.0
open-policy-agent>=0.60.0

# Envoy (deployment)
envoy>=1.28.0

# Decision Logging
asyncpg>=0.29.0  # PostgreSQL async driver
aioredis>=2.0.0  # Redis for caching
```

### Infrastructure
- OPA server (sidecar or standalone)
- Envoy proxy
- PostgreSQL (for decision logs)
- Redis (for rate limiting, caching)

---

## Configuration Files

### NeMo Guardrails Config
`guardrails/config.yml` - See section 1

### OPA Policies
- `policies/tool_calls.rego` - Tool call validation
- `policies/ingress.rego` - API ingress policies
- `policies/approval.rego` - Human approval rules

### Envoy Config
`envoy.yaml` - See section 3

---

## Testing Strategy

1. **Unit Tests**: Policy logic, validation functions
2. **Integration Tests**: OPA policies, NeMo Guardrails
3. **E2E Tests**: Complete guardrails flow
4. **Policy Tests**: OPA test framework
5. **Performance Tests**: Latency, throughput

---

## Monitoring & Observability

1. **Metrics**:
   - Policy decision rates (allow/deny)
   - Approval request rates
   - Guardrails violation rates
   - Policy evaluation latency

2. **Alerts**:
   - High denial rates
   - Approval timeout rates
   - Guardrails violations
   - Policy evaluation failures

3. **Dashboards**:
   - Policy effectiveness
   - Approval workflow status
   - Guardrails performance
   - Compliance metrics

---

## Conclusion

This architecture provides **minimum viable production guardrails** with:
- ✅ **NeMo Guardrails** for LLM I/O validation
- ✅ **OPA embedded** for tool call validation
- ✅ **Envoy + OPA** for API ingress policies
- ✅ **Decision logging** for audit and compliance
- ✅ **Policy-driven approval** workflows

**Status**: Architecture design complete - ready for implementation review

---

*This document is for review purposes. No code changes have been made.*
