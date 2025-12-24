# Policy Decisions Reference

All policy decisions are **automatically logged** when using `agent-observable-core`. This document provides a complete reference of policy decision logging.

## Decision Types

### Tool Call Validation

**Decision Type:** `tool_call`

**When:** Tool calls are validated against OPA policies

**Fields:**
- `decision_id` - Unique decision ID (UUID)
- `timestamp` - Decision timestamp (ISO 8601)
- `decision_type` - `"tool_call"`
- `result` - `"allow"`, `"deny"`, or `"requires_approval"`
- `tool_name` - Tool name
- `agent_id` - Agent identifier
- `context` - Additional context (tool parameters, etc.)

**Example:**
```json
{
  "decision_id": "abc123-def456-ghi789",
  "timestamp": "2025-12-24T12:00:00Z",
  "decision_type": "tool_call",
  "result": "allow",
  "tool_name": "create_task",
  "agent_id": "PlannerAgent",
  "context": {
    "parameters": {"title": "Test task"}
  }
}
```

### OPA Policy Decision

**Decision Type:** `opa`

**When:** OPA policy engine evaluates a request

**Fields:**
- `decision_id` - Unique decision ID (UUID)
- `timestamp` - Decision timestamp (ISO 8601)
- `decision_type` - `"opa"`
- `result` - `"allow"`, `"deny"`, or `"requires_approval"`
- `policy_name` - OPA policy name
- `agent_id` - Agent identifier
- `context` - Policy input context

**Example:**
```json
{
  "decision_id": "xyz789-abc123-def456",
  "timestamp": "2025-12-24T12:00:00Z",
  "decision_type": "opa",
  "result": "deny",
  "policy_name": "tool_access_policy",
  "agent_id": "ExecutorAgent",
  "context": {
    "tool": "delete_task",
    "user_role": "viewer"
  }
}
```

### Guardrails Decision

**Decision Type:** `guardrails`

**When:** NeMo Guardrails validates input/output

**Fields:**
- `decision_id` - Unique decision ID (UUID)
- `timestamp` - Decision timestamp (ISO 8601)
- `decision_type` - `"guardrails"`
- `result` - `"allow"` or `"deny"`
- `check_type` - `"input"` or `"output"`
- `agent_id` - Agent identifier
- `context` - Guardrails validation context

**Example:**
```json
{
  "decision_id": "guard123-abc456-def789",
  "timestamp": "2025-12-24T12:00:00Z",
  "decision_type": "guardrails",
  "result": "deny",
  "check_type": "input",
  "agent_id": "PlannerAgent",
  "context": {
    "reason": "Toxic content detected",
    "confidence": 0.95
  }
}
```

### Human Review Decision

**Decision Type:** `human_review`

**When:** Human reviewer approves/rejects a decision

**Fields:**
- `decision_id` - Unique decision ID (UUID)
- `timestamp` - Decision timestamp (ISO 8601)
- `decision_type` - `"human_review"`
- `result` - `"approve"` or `"reject"`
- `reviewer_id` - Reviewer identifier
- `original_decision_id` - Original decision ID being reviewed
- `context` - Review context

**Example:**
```json
{
  "decision_id": "review123-abc456-def789",
  "timestamp": "2025-12-24T12:00:00Z",
  "decision_type": "human_review",
  "result": "approve",
  "reviewer_id": "user123",
  "original_decision_id": "xyz789-abc123-def456",
  "context": {
    "reason": "Approved after manual review"
  }
}
```

## Decision Storage

### JSONL Format

Decisions are logged to `decision_logs.jsonl` (one JSON object per line):

```
{"decision_id": "abc123", "timestamp": "2025-12-24T12:00:00Z", ...}
{"decision_id": "def456", "timestamp": "2025-12-24T12:01:00Z", ...}
{"decision_id": "ghi789", "timestamp": "2025-12-24T12:02:00Z", ...}
```

### Batch Processing

Decisions are batched for performance:
- **Batch Size:** 100 decisions (default)
- **Flush Interval:** 5 seconds (default)
- **Automatic Flush:** On shutdown

### Elasticsearch Integration

Decisions can be shipped to Elasticsearch:
- **Index Pattern:** `decision-logs-*`
- **Format:** JSON documents
- **Searchable:** All fields are searchable

## Viewing Decisions

### Local File

```bash
# View latest decisions
tail -f decision_logs.jsonl | jq

# Count decisions
wc -l decision_logs.jsonl

# Search for specific decision
grep "tool_call" decision_logs.jsonl | jq
```

### Kibana

1. **Open Kibana:** http://localhost:5601
2. **Create Index Pattern:** `decision-logs-*`
3. **Discover:** Search and filter decisions
4. **Visualize:** Create dashboards

### Query Examples

**Find all denied decisions:**
```json
{
  "query": {
    "term": {
      "result": "deny"
    }
  }
}
```

**Find tool call decisions:**
```json
{
  "query": {
    "term": {
      "decision_type": "tool_call"
    }
  }
}
```

**Find decisions by agent:**
```json
{
  "query": {
    "term": {
      "agent_id": "PlannerAgent"
    }
  }
}
```

## Decision Metrics

Policy decisions automatically update metrics:

- `policy.violations.total` - Total policy violations
- `agent.{name}.policy.violations` - Violations per agent

## Audit Trail

All decisions create a complete audit trail:
- **Who:** Agent ID, reviewer ID
- **What:** Decision type, tool name, policy name
- **When:** Timestamp
- **Why:** Context, reason
- **Result:** Allow, deny, requires approval

This enables:
- **Compliance** - Full audit trail for compliance
- **Debugging** - Understand why decisions were made
- **Analytics** - Analyze decision patterns
- **Security** - Track policy violations

See [DOCKER_TOOLS.md](DOCKER_TOOLS.md) for complete setup instructions.
