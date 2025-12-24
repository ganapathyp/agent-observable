# Direct Data Generation Guide

**Purpose:** This guide explains how to directly generate logs, traces, and policy decisions to simulate demo scenarios in Docker tools without running actual workflows. Use this for demos, testing, or showcasing observability capabilities.

**No Coding Required Yet** - This document outlines requirements, formats, and approaches.

---

## Table of Contents

1. [Overview](#overview)
2. [Logs Generation](#logs-generation)
3. [Traces Generation](#traces-generation)
4. [Policy Decisions Generation](#policy-decisions-generation)
5. [Metrics Generation](#metrics-generation)
6. [Data Flow & Requirements](#data-flow--requirements)
7. [File Formats & Locations](#file-formats--locations)
8. [API Endpoints & Protocols](#api-endpoints--protocols)
9. [Tools & Dependencies](#tools--dependencies)
10. [Example Data Structures](#example-data-structures)
11. [Simulation Scenarios](#simulation-scenarios)

---

## Overview

### Current Data Flow

**Logs:**
```
Application → logs/taskpilot.log (JSON) → Filebeat → Elasticsearch → Kibana
```

**Traces:**
```
Application → OpenTelemetry SDK → OTLP gRPC (port 4317) → OTEL Collector → Jaeger
```

**Policy Decisions:**
```
Application → decision_logs.jsonl (JSONL) → [Filebeat] → Elasticsearch → Kibana
```

**Metrics:**
```
Application → /metrics endpoint (Prometheus format) → Prometheus → Grafana
```

### Direct Generation Requirements

To simulate data directly, you need to:

1. **Logs**: Write JSON-formatted log entries to `logs/taskpilot.log`
2. **Traces**: Send OTLP spans via gRPC to `localhost:4317` (OTEL Collector)
3. **Policy Decisions**: Write JSONL entries to `decision_logs.jsonl` (or use Elasticsearch API)
4. **Metrics**: Update metrics via `MetricsCollector` API

---

## Logs Generation

### File Location

**Path:** `examples/taskpilot/logs/taskpilot.log`

**Mounted in Docker:** `/var/log/taskpilot/taskpilot.log` (read by Filebeat)

### Format Requirements

**Format:** JSON (one JSON object per line)

**Required Fields:**
- `timestamp` - ISO 8601 timestamp (e.g., `2025-12-24T12:00:00.123Z`)
- `level` - Log level (INFO, ERROR, WARNING, DEBUG)
- `name` - Logger name (e.g., `taskpilot.core.middleware`)
- `message` - Log message

**Optional Fields (for correlation):**
- `request_id` - Request ID for correlation
- `agent_name` - Agent name
- `tool_name` - Tool name
- `task_id` - Task identifier
- `latency_ms` - Latency in milliseconds
- `error_code` - Error code (if error)
- `error_type` - Error type (if error)

### Example Log Entry

```json
{
  "timestamp": "2025-12-24T12:00:00.123Z",
  "level": "INFO",
  "name": "taskpilot.core.middleware",
  "message": "[AUDIT] PlannerAgent Input: Create a comprehensive task",
  "request_id": "req-abc123-def456-ghi789",
  "agent_name": "PlannerAgent",
  "latency_ms": 1234.56
}
```

### How Filebeat Processes Logs

**Filebeat Configuration:** `observability/filebeat/filebeat.yml`

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/taskpilot/*.log
    json.keys_under_root: true  # Flattens JSON fields to root level
    json.add_error_key: true
```

**Index Pattern:** `taskpilot-logs-*` (date-based: `taskpilot-logs-2025.12.24`)

**Time Field:** `@timestamp` (auto-extracted from `timestamp` field)

**Processing:** Filebeat automatically:
- Parses JSON
- Extracts `timestamp` → `@timestamp`
- Flattens JSON fields to root level
- Ships to Elasticsearch

### Direct Write Requirements

**To write logs directly:**

1. **File Path:** `examples/taskpilot/logs/taskpilot.log`
2. **Format:** JSON, one object per line
3. **Encoding:** UTF-8
4. **Append Mode:** Append to existing file (don't overwrite)
5. **Filebeat:** Automatically picks up new lines (polls every few seconds)

**No special tools needed** - Just write JSON lines to the file.

**Example (Python):**
```python
import json
from datetime import datetime

log_entry = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "level": "INFO",
    "name": "taskpilot.core.middleware",
    "message": "Workflow started",
    "request_id": "req-123"
}

with open("logs/taskpilot.log", "a") as f:
    f.write(json.dumps(log_entry) + "\n")
```

---

## Traces Generation

### Export Endpoint

**OTLP gRPC Endpoint:** `localhost:4317` (or `otel-collector:4317` from Docker)

**OTLP HTTP Endpoint:** `localhost:4318` (alternative, less common)

### Protocol Requirements

**Protocol:** OTLP (OpenTelemetry Protocol) over gRPC

**Service:** `opentelemetry.proto.collector.trace.v1.TraceService`

**Method:** `Export` (streaming)

### Trace Structure Requirements

**Required Components:**
1. **Resource** - Service name, version
2. **Trace ID** - 16-byte trace identifier (32 hex chars)
3. **Span ID** - 8-byte span identifier (16 hex chars)
4. **Parent Span ID** - 8-byte (if child span, null for root)
5. **Span Name** - Operation name (e.g., `taskpilot.workflow.run`)
6. **Start Time** - Unix nanoseconds (since epoch)
7. **End Time** - Unix nanoseconds
8. **Attributes** - Key-value pairs (tags)
9. **Status** - OK, ERROR, UNSET

### Example Trace Structure

**Workflow Span (Root):**
```json
{
  "resource": {
    "service.name": "taskpilot",
    "service.version": "1.0.0"
  },
  "trace_id": "1a1c5bfce14c49ab82b4dd532ce128d2",
  "span_id": "05596eeef8660a42",
  "parent_span_id": null,
  "name": "taskpilot.workflow.run",
  "start_time": 1766519003876590000,
  "end_time": 1766519003990776000,
  "duration_ns": 114186000,
  "attributes": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "workflow.type": "task_creation",
    "workflow.success": "true",
    "workflow.latency.ms": "114.186"
  },
  "status": "OK"
}
```

**Agent Span (Child of Workflow):**
```json
{
  "trace_id": "1a1c5bfce14c49ab82b4dd532ce128d2",
  "span_id": "1b2c3d4e5f6a7b8c",
  "parent_span_id": "05596eeef8660a42",
  "name": "taskpilot.agent.PlannerAgent.run",
  "start_time": 1766519003877000000,
  "end_time": 1766519003990000000,
  "duration_ns": 113000000,
  "attributes": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "agent_name": "PlannerAgent",
    "latency_ms": "113.0",
    "output_length": "500"
  },
  "status": "OK"
}
```

**Tool Span (Child of Agent):**
```json
{
  "trace_id": "1a1c5bfce14c49ab82b4dd532ce128d2",
  "span_id": "2c3d4e5f6a7b8c9d",
  "parent_span_id": "1b2c3d4e5f6a7b8c",
  "name": "taskpilot.tool.create_task.call",
  "start_time": 1766519003900000000,
  "end_time": 1766519003950000000,
  "duration_ns": 50000000,
  "attributes": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "tool_name": "create_task",
    "latency_ms": "50.0"
  },
  "status": "OK"
}
```

### Direct Export Requirements

**To write traces directly:**

1. **Use OpenTelemetry SDK** (Python: `opentelemetry-api`, `opentelemetry-sdk`)
2. **Create TracerProvider** with OTLP exporter
3. **Create spans** with proper parent-child relationships
4. **Export via OTLP gRPC** to `localhost:4317`

**Required Libraries:**
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp-proto-grpc`
- `grpcio` (dependency)

**Example (Python):**
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Setup
resource = Resource.create({"service.name": "taskpilot"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

# Create trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("taskpilot.workflow.run") as workflow_span:
    workflow_span.set_attribute("request.id", "req-123")
    with tracer.start_as_current_span("taskpilot.agent.PlannerAgent.run") as agent_span:
        agent_span.set_attribute("agent_name", "PlannerAgent")
```

---

## Policy Decisions Generation

### File Location

**Path:** `examples/taskpilot/decision_logs.jsonl`

**Note:** Filebeat currently reads `logs/taskpilot.log`, not `decision_logs.jsonl`. Options:
1. Write decisions to `logs/taskpilot.log` with `log_type: "policy_decision"`
2. Update Filebeat config to read `decision_logs.jsonl`
3. Use Elasticsearch API directly

### Format Requirements

**Format:** JSONL (one JSON object per line)

**Required Fields:**
- `decision_id` - Unique decision ID (UUID)
- `timestamp` - ISO 8601 timestamp
- `decision_type` - Type: `tool_call`, `opa`, `guardrails`, `human_review`
- `result` - Result: `allow`, `deny`, `requires_approval`

**Optional Fields:**
- `tool_name` - Tool name (if applicable)
- `agent_id` - Agent identifier
- `policy_name` - Policy name (if OPA)
- `reason` - Decision reason
- `context` - Additional context (dict)

### Example Decision Entry

```json
{
  "decision_id": "abc123-def456-ghi789",
  "timestamp": "2025-12-24T12:00:00.123Z",
  "decision_type": "tool_call",
  "result": "allow",
  "tool_name": "create_task",
  "agent_id": "PlannerAgent",
  "reason": "Policy check passed",
  "context": {
    "parameters": {"title": "Test task"},
    "user_role": "admin"
  }
}
```

### Direct Write Requirements

**Option 1: Write to `decision_logs.jsonl`**
1. **File Path:** `examples/taskpilot/decision_logs.jsonl`
2. **Format:** JSONL, one object per line
3. **Encoding:** UTF-8
4. **Append Mode:** Append to existing file

**Option 2: Write to `logs/taskpilot.log` (Recommended)**
1. **File Path:** `examples/taskpilot/logs/taskpilot.log`
2. **Format:** JSON with `log_type: "policy_decision"`
3. **Filebeat:** Automatically ships to Elasticsearch

**Option 3: Use Elasticsearch API Directly**
1. **Endpoint:** `http://localhost:9200/decision-logs-2025.12.24/_doc`
2. **Method:** POST
3. **Format:** JSON

---

## Metrics Generation

### Current Implementation

**Storage:** In-memory `MetricsCollector` (not file-based)

**Export:** Via `/metrics` endpoint (Prometheus format)

### Direct Update Requirements

**Option 1: Use MetricsCollector API**
```python
from agent_observable_core.observability import MetricsCollector

metrics = MetricsCollector()
metrics.increment_counter("workflow.runs", 1.0)
metrics.increment_counter("llm.cost.total", 0.05)
metrics.record_histogram("workflow.latency_ms", 2500.0)
```

**Option 2: Update via Application**
- Access the global `MetricsCollector` instance
- Use the API to update metrics
- Metrics automatically exported via `/metrics` endpoint

**Option 3: Direct Prometheus Push (Not Standard)**
- Prometheus typically pulls (scrapes), doesn't push
- Would need Pushgateway (not in current setup)

---

## Data Flow & Requirements

### Logs Flow

```
┌─────────────────┐
│ Direct Write    │
│ (JSON to file)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ logs/           │
│ taskpilot.log   │
└────────┬────────┘
         │
         │ (mounted volume)
         ▼
┌─────────────────┐
│ Filebeat        │
│ (polls file)    │
└────────┬────────┘
         │
         │ (HTTP API)
         ▼
┌─────────────────┐
│ Elasticsearch   │
│ (indexes logs)  │
└────────┬────────┘
         │
         │ (queries)
         ▼
┌─────────────────┐
│ Kibana          │
│ (visualizes)    │
└─────────────────┘
```

**Requirements:**
- ✅ Write JSON to `logs/taskpilot.log`
- ✅ Filebeat automatically picks up new lines
- ✅ No manual intervention needed

### Traces Flow

```
┌─────────────────┐
│ Direct Export   │
│ (OTLP gRPC)     │
└────────┬────────┘
         │
         │ (gRPC:4317)
         ▼
┌─────────────────┐
│ OTEL Collector  │
│ (receives)      │
└────────┬────────┘
         │
         │ (OTLP HTTP)
         ▼
┌─────────────────┐
│ Jaeger          │
│ (stores)        │
└────────┬────────┘
         │
         │ (UI queries)
         ▼
┌─────────────────┐
│ Jaeger UI       │
│ (visualizes)    │
└─────────────────┘
```

**Requirements:**
- ✅ OpenTelemetry SDK
- ✅ OTLP gRPC client
- ✅ Proper trace/span structure
- ✅ Service name configuration

### Policy Decisions Flow

```
┌─────────────────┐
│ Direct Write    │
│ (JSONL to file) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ decision_      │
│ logs.jsonl      │
└────────┬────────┘
         │
         │ (Option 1: Filebeat)
         │ (Option 2: ES API)
         ▼
┌─────────────────┐
│ Elasticsearch   │
│ (indexes)       │
└────────┬────────┘
         │
         │ (queries)
         ▼
┌─────────────────┐
│ Kibana          │
│ (visualizes)    │
└─────────────────┘
```

**Requirements:**
- ✅ Write JSONL to `decision_logs.jsonl` OR
- ✅ Write to `logs/taskpilot.log` with `log_type: "policy_decision"` OR
- ✅ Use Elasticsearch API directly

---

## File Formats & Locations

### Logs

**File:** `examples/taskpilot/logs/taskpilot.log`

**Format:** JSON (one object per line)

**Example:**
```json
{"timestamp": "2025-12-24T12:00:00Z", "level": "INFO", "name": "taskpilot", "message": "Workflow started", "request_id": "req-123"}
{"timestamp": "2025-12-24T12:00:01Z", "level": "INFO", "name": "taskpilot", "message": "Agent executed", "request_id": "req-123", "agent_name": "PlannerAgent"}
```

**Docker Mount:** `/var/log/taskpilot/taskpilot.log` (read by Filebeat)

**Index Pattern:** `taskpilot-logs-*` (in Kibana)

### Traces

**Export:** OTLP gRPC to `localhost:4317`

**Format:** OTLP protobuf (via OpenTelemetry SDK)

**No file** - Direct export to OTEL Collector

**Service Name:** `taskpilot` (configured in Resource)

### Policy Decisions

**File:** `examples/taskpilot/decision_logs.jsonl`

**Format:** JSONL (one object per line)

**Example:**
```json
{"decision_id": "abc123", "timestamp": "2025-12-24T12:00:00Z", "decision_type": "tool_call", "result": "allow", "tool_name": "create_task"}
{"decision_id": "def456", "timestamp": "2025-12-24T12:00:01Z", "decision_type": "opa", "result": "deny", "reason": "Unauthorized"}
```

**Alternative:** Write to `logs/taskpilot.log` with `log_type: "policy_decision"`

**Index Pattern:** `taskpilot-logs-*` or `decision-logs-*` (in Kibana)

---

## API Endpoints & Protocols

### Prometheus Metrics

**Endpoint:** `http://localhost:8000/metrics`

**Format:** Prometheus text format

**Protocol:** HTTP GET

**Example:**
```
# TYPE llm_cost_total counter
llm_cost_total 0.123456

# TYPE workflow_runs counter
workflow_runs 100
```

**Direct Update:** Use `MetricsCollector` API:
```python
metrics_collector.increment_counter("workflow.runs", 1.0)
metrics_collector.increment_counter("llm.cost.total", 0.05)
```

### OpenTelemetry Traces

**Endpoint:** `localhost:4317` (gRPC)

**Protocol:** OTLP over gRPC

**Service:** `opentelemetry.proto.collector.trace.v1.TraceService`

**Method:** `Export`

**Alternative:** HTTP endpoint at `localhost:4318` (OTLP HTTP)

### Elasticsearch API

**Endpoint:** `http://localhost:9200`

**Protocol:** HTTP REST API

**Index Logs:**
```bash
POST http://localhost:9200/taskpilot-logs-2025.12.24/_doc
Content-Type: application/json

{
  "@timestamp": "2025-12-24T12:00:00Z",
  "level": "INFO",
  "message": "Workflow started",
  "request_id": "req-123"
}
```

**Index Decisions:**
```bash
POST http://localhost:9200/decision-logs-2025.12.24/_doc
Content-Type: application/json

{
  "@timestamp": "2025-12-24T12:00:00Z",
  "decision_type": "tool_call",
  "result": "allow",
  "tool_name": "create_task"
}
```

**Bulk Index (Multiple Documents):**
```bash
POST http://localhost:9200/_bulk
Content-Type: application/x-ndjson

{"index": {"_index": "taskpilot-logs-2025.12.24"}}
{"@timestamp": "2025-12-24T12:00:00Z", "level": "INFO", "message": "Log 1"}
{"index": {"_index": "taskpilot-logs-2025.12.24"}}
{"@timestamp": "2025-12-24T12:00:01Z", "level": "INFO", "message": "Log 2"}
```

### Jaeger API

**Endpoint:** `http://localhost:16686/api`

**Protocol:** HTTP REST API

**Query Traces:**
```bash
GET http://localhost:16686/api/traces?service=taskpilot&limit=10
```

**Note:** Jaeger typically receives traces via OTEL Collector, not direct API writes. Use OTLP export instead.

---

## Tools & Dependencies

### For Logs Generation

**Minimal Requirements:**
- ✅ File write access to `logs/taskpilot.log`
- ✅ JSON formatting capability
- ✅ UTF-8 encoding

**No special libraries needed** - Can use any language/tool that can write JSON to a file.

**Example Tools:**
- Python: `json` module + file I/O
- Bash: `jq` or `echo` with JSON
- Node.js: `fs.writeFile` with `JSON.stringify`
- curl: Can't write files directly, but can use scripts

### For Traces Generation

**Required Libraries:**
- `opentelemetry-api` - OpenTelemetry API
- `opentelemetry-sdk` - OpenTelemetry SDK
- `opentelemetry-exporter-otlp-proto-grpc` - OTLP gRPC exporter
- `grpcio` - gRPC library (dependency)

**Alternative:** Use HTTP endpoint if available (less common)

**Example Tools:**
- Python: OpenTelemetry SDK (recommended)
- Go: OpenTelemetry Go SDK
- Java: OpenTelemetry Java SDK
- curl: Not suitable (needs gRPC/protobuf)

### For Policy Decisions Generation

**Minimal Requirements:**
- ✅ File write access to `decision_logs.jsonl` OR
- ✅ File write access to `logs/taskpilot.log` OR
- ✅ HTTP client for Elasticsearch API

**No special libraries needed** - Same as logs.

**Alternative:** Use Elasticsearch API directly (requires `requests` library or curl)

### For Metrics Generation

**Required:**
- ✅ Access to `MetricsCollector` instance (Python API), OR
- ✅ HTTP client to update metrics (if API endpoint exists)

**Current Implementation:** In-memory `MetricsCollector` - would need to use the Python API.

---

## Example Data Structures

### Log Entry Structure

**Standard Log:**
```json
{
  "timestamp": "2025-12-24T12:00:00.123Z",
  "level": "INFO",
  "name": "taskpilot.core.middleware",
  "message": "[AUDIT] PlannerAgent Input: Create a task",
  "request_id": "req-abc123-def456-ghi789",
  "agent_name": "PlannerAgent",
  "tool_name": "create_task",
  "task_id": "task-123",
  "latency_ms": 1234.56
}
```

**Error Log:**
```json
{
  "timestamp": "2025-12-24T12:00:00.123Z",
  "level": "ERROR",
  "name": "taskpilot.core.middleware",
  "message": "[ERROR] Tool execution failed",
  "request_id": "req-abc123",
  "agent_name": "ExecutorAgent",
  "tool_name": "update_task",
  "error_code": "TOOL_TIMEOUT",
  "error_type": "ToolTimeoutError",
  "error_message": "Tool execution exceeded 30s timeout"
}
```

**Policy Decision Log (in taskpilot.log):**
```json
{
  "timestamp": "2025-12-24T12:00:00.123Z",
  "level": "INFO",
  "name": "agent_observable_policy.decision_logger",
  "message": "[POLICY] tool_call decision: allow",
  "log_type": "policy_decision",
  "decision_id": "abc123-def456-ghi789",
  "decision_type": "tool_call",
  "result": "allow",
  "tool_name": "create_task",
  "agent_id": "PlannerAgent",
  "reason": "Policy check passed"
}
```

### Trace Span Structure

**Workflow Span (Root):**
```json
{
  "resource": {
    "service.name": "taskpilot",
    "service.version": "1.0.0"
  },
  "trace_id": "1a1c5bfce14c49ab82b4dd532ce128d2",
  "span_id": "05596eeef8660a42",
  "parent_span_id": null,
  "name": "taskpilot.workflow.run",
  "start_time": 1766519003876590000,
  "end_time": 1766519003990776000,
  "duration_ns": 114186000,
  "attributes": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "workflow.type": "task_creation",
    "workflow.success": "true",
    "workflow.latency.ms": "114.186"
  },
  "status": "OK"
}
```

**Agent Span (with error):**
```json
{
  "trace_id": "1a1c5bfce14c49ab82b4dd532ce128d2",
  "span_id": "1b2c3d4e5f6a7b8c",
  "parent_span_id": "05596eeef8660a42",
  "name": "taskpilot.agent.ExecutorAgent.run",
  "start_time": 1766519004000000,
  "end_time": 1766519004500000,
  "duration_ns": 500000,
  "attributes": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "agent_name": "ExecutorAgent",
    "error": "true",
    "error.message": "Tool execution failed",
    "error.code": "TOOL_TIMEOUT"
  },
  "status": "ERROR",
  "events": [
    {
      "name": "exception",
      "time": 1766519004500000,
      "attributes": {
        "exception.type": "ToolTimeoutError",
        "exception.message": "Tool execution exceeded timeout"
      }
    }
  ]
}
```

### Policy Decision Structure

**Tool Call Decision:**
```json
{
  "decision_id": "abc123-def456-ghi789",
  "timestamp": "2025-12-24T12:00:00.123Z",
  "decision_type": "tool_call",
  "result": "allow",
  "tool_name": "create_task",
  "agent_id": "PlannerAgent",
  "reason": "Policy check passed",
  "context": {
    "parameters": {"title": "Test task"},
    "user_role": "admin"
  }
}
```

**OPA Decision (Denied):**
```json
{
  "decision_id": "xyz789-abc123-def456",
  "timestamp": "2025-12-24T12:00:01.456Z",
  "decision_type": "opa",
  "result": "deny",
  "policy_name": "tool_access_policy",
  "agent_id": "ExecutorAgent",
  "reason": "Unauthorized tool access",
  "context": {
    "tool": "delete_task",
    "user_role": "viewer",
    "policy_input": {
      "tool": "delete_task",
      "user": "viewer",
      "resource": "task"
    }
  }
}
```

**Guardrails Decision:**
```json
{
  "decision_id": "guard123-abc456-def789",
  "timestamp": "2025-12-24T12:00:02.789Z",
  "decision_type": "guardrails",
  "result": "deny",
  "check_type": "input",
  "agent_id": "PlannerAgent",
  "reason": "Toxic content detected",
  "context": {
    "confidence": 0.95,
    "detected_category": "toxicity"
  }
}
```

---

## Simulation Scenarios

### Scenario 1: Cost Optimization Demo

**Generate:**
- **Logs:** 100 workflow execution logs with different models
- **Metrics:** Cost metrics for gpt-4o vs gpt-4o-mini
- **Traces:** Traces showing model usage

**Data Needed:**
- 50 workflows using gpt-4o (high cost: $0.10 each)
- 50 workflows using gpt-4o-mini (low cost: $0.02 each)
- Metrics: `llm_cost_model_gpt_4o = 5.0`, `llm_cost_model_gpt_4o_mini = 1.0`
- Token metrics: `llm_tokens_total_gpt_4o = 50000`, `llm_tokens_total_gpt_4o_mini = 50000`

**Files to Generate:**
- `logs/taskpilot.log` - 100 log entries
- Metrics via `MetricsCollector` API
- Traces via OTLP (50 traces with gpt-4o, 50 with gpt-4o-mini)

### Scenario 2: Performance Bottleneck Demo

**Generate:**
- **Traces:** 20 slow traces with hierarchy
- **Logs:** Error logs for slow operations
- **Metrics:** Latency metrics per agent

**Data Needed:**
- 20 traces with PlannerAgent (fast: 500ms) and ExecutorAgent (slow: 5000ms)
- Latency metrics: `agent_PlannerAgent_latency_ms_p95 = 500`, `agent_ExecutorAgent_latency_ms_p95 = 5000`
- Error logs for timeout scenarios

**Files to Generate:**
- Traces via OTLP (20 traces with slow ExecutorAgent)
- `logs/taskpilot.log` - 20 error log entries
- Metrics via `MetricsCollector` API

### Scenario 3: Policy Violation Demo

**Generate:**
- **Policy Decisions:** 10 denied decisions
- **Logs:** Policy violation logs
- **Metrics:** Policy violation metrics

**Data Needed:**
- 10 denied tool call decisions
- 5 denied OPA decisions
- Policy violation metrics: `policy_violations_total = 15`
- Logs with `error_code: "POLICY_VIOLATION"`

**Files to Generate:**
- `decision_logs.jsonl` - 15 decision entries (10 tool_call deny, 5 opa deny)
- OR `logs/taskpilot.log` - 15 log entries with `log_type: "policy_decision"`
- Metrics via `MetricsCollector` API

### Scenario 4: Error Pattern Demo

**Generate:**
- **Logs:** Various error types
- **Traces:** Error traces
- **Metrics:** Error rates

**Data Needed:**
- 20 TOOL_TIMEOUT errors
- 10 TOOL_EXECUTION_ERROR errors
- 5 POLICY_VIOLATION errors
- Error metrics: `tool_create_task_errors = 20`, `agent_ExecutorAgent_errors = 10`
- Traces with `status: "ERROR"`

**Files to Generate:**
- `logs/taskpilot.log` - 35 error log entries
- Traces via OTLP (35 error traces)
- Metrics via `MetricsCollector` API

---

## Requirements Summary

### Minimal Requirements (File-Based)

**For Logs:**
- ✅ Write access to `logs/taskpilot.log`
- ✅ JSON formatting
- ✅ UTF-8 encoding
- ✅ One JSON object per line

**For Policy Decisions:**
- ✅ Write access to `decision_logs.jsonl` OR `logs/taskpilot.log`
- ✅ JSON/JSONL formatting
- ✅ UTF-8 encoding
- ✅ One JSON object per line

**For Metrics:**
- ✅ Access to `MetricsCollector` API (Python)
- ✅ OR update via application endpoint

### Advanced Requirements (API-Based)

**For Traces:**
- ✅ OpenTelemetry SDK (`opentelemetry-api`, `opentelemetry-sdk`)
- ✅ OTLP gRPC exporter (`opentelemetry-exporter-otlp-proto-grpc`)
- ✅ gRPC libraries (`grpcio`)
- ✅ Proper trace/span structure
- ✅ Service name configuration

**For Direct Elasticsearch:**
- ✅ HTTP client (`requests` library or curl)
- ✅ Elasticsearch API knowledge
- ✅ Index mapping knowledge
- ✅ Bulk API for multiple documents

---

## Quick Reference

| Data Type | Write Method | Format | Location/Endpoint | Tools Needed |
|-----------|--------------|--------|-------------------|--------------|
| **Logs** | File write | JSON (one per line) | `logs/taskpilot.log` | Any (Python, bash, etc.) |
| **Traces** | OTLP gRPC | Protobuf | `localhost:4317` | OpenTelemetry SDK |
| **Decisions** | File write | JSONL (one per line) | `decision_logs.jsonl` OR `logs/taskpilot.log` | Any (Python, bash, etc.) |
| **Decisions (ES)** | HTTP API | JSON | `http://localhost:9200/decision-logs-*/_doc` | HTTP client |
| **Metrics** | Python API | In-memory | `MetricsCollector` API | Python |

**Filebeat:** Automatically reads `logs/taskpilot.log` and ships to Elasticsearch (polls every few seconds).

**OTEL Collector:** Automatically receives OTLP traces on port 4317 and forwards to Jaeger.

**Prometheus:** Automatically scrapes `/metrics` endpoint every 15 seconds.

---

## Next Steps

1. **Choose Approach:**
   - File-based (simpler, for logs/decisions)
   - API-based (for traces, direct Elasticsearch)

2. **Prepare Data:**
   - Create example JSON structures
   - Generate realistic timestamps
   - Create correlated request IDs

3. **Write Scripts/Tools:**
   - Log generator script
   - Trace generator script
   - Decision generator script
   - Metrics updater script

4. **Verify in Tools:**
   - Check Prometheus for metrics
   - Check Jaeger for traces
   - Check Kibana for logs/decisions

5. **Run Demo Scenarios:**
   - Use scenarios from `METRICS_DEMO_SCENARIOS.md`
   - Generate data for each scenario
   - Showcase in Docker tools
