# Traces Reference

All traces are **automatically created** when using `agent-observable-core`. This document provides a complete reference of distributed tracing.

## Trace Hierarchy

Traces follow a hierarchical structure:

```
{service}.workflow.run (root span)
  ├─ {service}.agent.{name}.run (child span)
  │   ├─ {service}.tool.{name}.call (grandchild span)
  │   └─ {service}.tool.{name}.call (grandchild span)
  ├─ {service}.agent.{name}.run (child span)
  │   └─ {service}.tool.{name}.call (grandchild span)
  └─ {service}.agent.{name}.run (child span)
```

**Example:**
```
taskpilot.workflow.run
  ├─ taskpilot.agent.PlannerAgent.run
  │   └─ taskpilot.tool.create_task.call
  ├─ taskpilot.agent.ExecutorAgent.run
  │   └─ taskpilot.tool.update_task.call
  └─ taskpilot.agent.ReviewerAgent.run
      └─ taskpilot.tool.review_task.call
```

## Span Types

### Workflow Span

**Name:** `{service}.workflow.run`

**Attributes:**
- `request.id` - Request ID (UUID)
- `workflow.type` - Workflow type
- `workflow.success` - Success status (true/false)
- `workflow.latency.ms` - Workflow latency
- `span.kind` - Span kind (internal)

**Example:**
```json
{
  "operationName": "taskpilot.workflow.run",
  "tags": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "workflow.type": "task_creation",
    "workflow.success": "true",
    "workflow.latency.ms": "2500.0",
    "span.kind": "internal"
  }
}
```

### Agent Span

**Name:** `{service}.agent.{name}.run`

**Attributes:**
- `request.id` - Request ID (correlated with workflow)
- `agent_name` - Agent name
- `latency_ms` - Agent execution latency
- `output_length` - Output text length
- `span.kind` - Span kind (internal)

**Example:**
```json
{
  "operationName": "taskpilot.agent.PlannerAgent.run",
  "tags": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "agent_name": "PlannerAgent",
    "latency_ms": "1200.0",
    "output_length": "500",
    "span.kind": "internal"
  }
}
```

### Tool Span

**Name:** `{service}.tool.{name}.call`

**Attributes:**
- `request.id` - Request ID (correlated with workflow)
- `tool_name` - Tool name
- `latency_ms` - Tool execution latency
- `span.kind` - Span kind (internal)

**Example:**
```json
{
  "operationName": "taskpilot.tool.create_task.call",
  "tags": {
    "request.id": "1a1c5bfc-e14c-49ab-82b4-dd532ce128d2",
    "tool_name": "create_task",
    "latency_ms": "150.0",
    "span.kind": "internal"
  }
}
```

## Request ID Correlation

All spans in a workflow share the same `request.id`, enabling:
- **Trace correlation** - Find all spans for a request
- **Log correlation** - Correlate logs with traces
- **Error tracking** - Track errors across spans

**Example:**
```
Request ID: 1a1c5bfc-e14c-49ab-82b4-dd532ce128d2
  ├─ Workflow span: request.id = 1a1c5bfc-...
  ├─ Agent span: request.id = 1a1c5bfc-...
  └─ Tool span: request.id = 1a1c5bfc-...
```

## Error Tracking

Errors are automatically captured in spans:

**Error Attributes:**
- `error` - Error flag (true)
- `error.message` - Error message
- `error.code` - Error code (if available)
- `error.type` - Error type

**Example:**
```json
{
  "operationName": "taskpilot.agent.PlannerAgent.run",
  "tags": {
    "error": "true",
    "error.message": "Policy violation: 'delete' keyword detected",
    "error.code": "POLICY_VIOLATION",
    "error.type": "PolicyViolationError"
  }
}
```

## Viewing Traces

### Jaeger UI

1. **Open Jaeger:** http://localhost:16686
2. **Select Service:** Choose your service (e.g., `taskpilot`)
3. **Find Traces:** Click "Find Traces"
4. **View Trace:** Click on a trace to see the hierarchy

### Trace Details

In Jaeger, you can see:
- **Timeline** - When each span executed
- **Duration** - How long each span took
- **Tags** - All span attributes
- **Logs** - Span logs (if any)
- **Hierarchy** - Parent-child relationships

### Query Examples

**Find traces by service:**
```
Service: taskpilot
```

**Find traces with errors:**
```
Service: taskpilot
Tags: error=true
```

**Find traces by request ID:**
```
Service: taskpilot
Tags: request.id=1a1c5bfc-e14c-49ab-82b4-dd532ce128d2
```

## Trace Export

Traces are automatically exported:
1. **OpenTelemetry** - Created via OpenTelemetry SDK
2. **OTLP** - Exported to OpenTelemetry Collector (gRPC)
3. **Jaeger** - Collector forwards to Jaeger backend

**Configuration:**
- **OTLP Endpoint:** `http://localhost:4317` (default)
- **Service Name:** Set via `service_name` parameter
- **Batch Export:** Automatic batching for performance

## Performance

Tracing has minimal performance impact:
- **Async Export** - Traces exported asynchronously
- **Batch Processing** - Multiple spans batched together
- **Non-Blocking** - Export failures don't block execution

See [DOCKER_TOOLS.md](DOCKER_TOOLS.md) for complete setup instructions.
