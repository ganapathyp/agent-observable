# Observability Tools Walkthrough

Complete guide to using Jaeger, Prometheus, Grafana, Kibana, and other observability tools.

---

## 🚀 Quick Start: Generate Data First

**Before checking tools, you need to generate traces, logs, and metrics:**

### Step 1: Start Docker Services

```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/agent-observable/examples/taskpilot

# Start all observability services
docker-compose -f docker-compose.observability.yml up -d

# Verify all services are running
docker-compose -f docker-compose.observability.yml ps
```

**Expected**: 7 services running (Jaeger, Prometheus, Grafana, Elasticsearch, Kibana, Filebeat, OTEL Collector)

### Step 2: Activate Virtual Environment

```bash
source .venv/bin/activate
```

### Step 3: Run Workflow to Generate Data

**Option A: Run Once (Script Mode)**
```bash
python3 main.py
```

**Option B: Run as Server (Continuous Mode)**
```bash
python3 main.py --server --port 8000
# Keep running, workflows execute in background loop
```

**What This Generates**:
- ✅ **Traces**: Workflow and agent spans in Jaeger
- ✅ **Metrics**: Workflow/agent/tool metrics in Prometheus
- ✅ **Logs**: Application logs (if configured to write to files)
- ✅ **Policy Decisions**: Written to `decision_logs.jsonl`

### Step 4: Wait for Data Export

**Wait 2-3 seconds** after workflow completes for:
- Traces to be exported to Jaeger
- Metrics to be scraped by Prometheus
- Logs to be shipped to Elasticsearch (if Filebeat is configured)

---

## Table of Contents

1. [Quick Start: Generate Data](#-quick-start-generate-data-first)
2. [Jaeger (Distributed Tracing)](#jaeger)
3. [Prometheus (Metrics)](#prometheus)
4. [Grafana (Metrics Visualization)](#grafana)
5. [Kibana (Logs)](#kibana)
6. [Policy Decisions (Decision Logs)](#policy-decisions)
7. [Quick Reference](#quick-reference)

---

## 1. Jaeger (Distributed Tracing) 🔍

**URL**: http://localhost:16686

### How to Generate Traces

**Traces are automatically generated when you run a workflow**:
```bash
python3 main.py
```

**What gets traced**:
- Workflow execution (`taskpilot.workflow.run`)
- Each agent execution (`taskpilot.agent.*.run`)
- Tool calls (if instrumented)

**Wait 2-3 seconds** after workflow completes for traces to appear in Jaeger.

### What to Look For

#### A. Service List
1. **Open Jaeger UI**: http://localhost:16686
2. **Select Service**: `taskpilot` from dropdown
3. **Click "Find Traces"**

**What you should see**:
- List of traces with timestamps
- Each trace represents one workflow execution

#### B. Trace Hierarchy

**Click on any trace** to see the hierarchy:

```
Expected Structure:
└─ taskpilot.workflow.run (root span)
   ├─ taskpilot.agent.PlannerAgent.run (child)
   ├─ taskpilot.agent.ReviewerAgent.run (child)
   └─ taskpilot.agent.ExecutorAgent.run (child)
```

**What to check**:
- ✅ **Root span exists**: `taskpilot.workflow.run`
- ✅ **Child spans visible**: All 3 agent spans
- ✅ **Parent-child links**: Click on spans to see relationships
- ✅ **Duration**: Each span shows execution time

#### C. Span Details

**Click on any span** to see:
- **Tags**: `agent_name`, `agent_type`, `request_id`, `workflow_type`
- **Logs**: Input/output text, errors
- **Duration**: How long each agent took
- **Timeline**: Visual representation of execution order

**Key Tags to Look For**:
- `request.id`: Correlates all spans in a trace
- `agent_name`: Which agent executed
- `agent_type`: `planner`, `reviewer`, or `executor`
- `workflow.success`: `true` or `false`
- `workflow.latency.ms`: Total workflow duration

#### D. Search & Filter

**Use filters**:
- **Service**: `taskpilot`
- **Operation**: `taskpilot.workflow.run` or `taskpilot.agent.*.run`
- **Tags**: `agent_name=PlannerAgent`, `workflow.success=true`
- **Duration**: Find slow traces
- **Time Range**: Last 15 minutes, 1 hour, etc.

**Example Queries**:
- Find failed workflows: Tag `workflow.success=false`
- Find slow agents: Duration > 5000ms
- Find specific request: Tag `request.id=<your-request-id>`

---

## 2. Prometheus (Metrics) 📊

**URL**: http://localhost:9090

### How to Generate Metrics

**Metrics are automatically generated when you run a workflow**:
```bash
python3 main.py
```

**OR if running in server mode**:
```bash
python3 main.py --server --port 8000
# Metrics available at: http://localhost:8000/metrics
```

**What gets measured**:
- Workflow runs, success, errors, latency
- Agent invocations, success, errors, latency
- Tool calls, success, errors, latency
- Policy violations
- LLM cost and token usage

**Prometheus scrapes**:
- Every 15 seconds from `http://localhost:8000/metrics` (if server mode)
- OR metrics are in-memory (query via API if needed)

### What to Look For

#### A. Available Metrics

**Open Prometheus UI**: http://localhost:9090

**Key Metrics to Query**:

1. **Workflow Metrics**:
   ```promql
   workflow_runs_total
   workflow_success_total
   workflow_errors_total
   workflow_latency_ms_bucket
   ```

2. **Agent Metrics**:
   ```promql
   agent_PlannerAgent_invocations_total
   agent_ReviewerAgent_invocations_total
   agent_ExecutorAgent_invocations_total
   agent_PlannerAgent_success_total
   agent_PlannerAgent_errors_total
   ```

3. **Tool Metrics**:
   ```promql
   tool_create_task_calls_total
   tool_create_task_success_total
   tool_create_task_errors_total
   tool_create_task_latency_ms
   ```

4. **Policy Metrics**:
   ```promql
   policy_violations_total
   ```

5. **LLM Metrics**:
   ```promql
   llm_cost_total
   llm_tokens_input_total
   llm_tokens_output_total
   ```

#### B. Query Examples

**1. Total Workflow Runs**:
```promql
sum(workflow_runs_total)
```

**2. Success Rate**:
```promql
sum(workflow_success_total) / sum(workflow_runs_total) * 100
```

**3. Average Workflow Latency**:
```promql
rate(workflow_latency_ms_sum[5m]) / rate(workflow_latency_ms_count[5m])
```

**4. Agent Invocation Count**:
```promql
sum(rate(agent_PlannerAgent_invocations_total[5m]))
```

**5. Policy Violation Rate**:
```promql
rate(policy_violations_total[5m])
```

**6. Total LLM Cost**:
```promql
sum(llm_cost_total)
```

#### C. Graph Visualization

1. **Enter query** in "Expression" box
2. **Click "Execute"**
3. **View Graph** tab to see trends over time
4. **View Table** tab to see current values

#### D. Alerts (Optional)

**Example Alert Rules**:
```yaml
- alert: HighErrorRate
  expr: rate(workflow_errors_total[5m]) > 0.1
  annotations:
    summary: "High workflow error rate"

- alert: SlowWorkflows
  expr: histogram_quantile(0.95, workflow_latency_ms_bucket) > 10000
  annotations:
    summary: "P95 latency exceeds 10 seconds"
```

---

## 3. Grafana (Metrics Visualization) 📈

**URL**: http://localhost:3000

### Setup

1. **Open Grafana**: http://localhost:3000
2. **Default credentials**: `admin` / `admin` (change on first login)
3. **Add Prometheus Data Source**:
   - Configuration → Data Sources → Add data source
   - Type: Prometheus
   - URL: `http://prometheus:9090`
   - Click "Save & Test"

### What to Look For

#### A. Create Dashboard

**1. Create New Dashboard**:
- Click "+" → "Create Dashboard"
- Click "Add visualization"

**2. Key Panels to Create**:

**Panel 1: Workflow Runs**
```promql
sum(rate(workflow_runs_total[5m]))
```
- **Visualization**: Graph
- **Title**: "Workflow Runs per Second"

**Panel 2: Success Rate**
```promql
sum(rate(workflow_success_total[5m])) / sum(rate(workflow_runs_total[5m])) * 100
```
- **Visualization**: Stat
- **Title**: "Success Rate %"
- **Unit**: Percent (0-100)

**Panel 3: P95 Latency**
```promql
histogram_quantile(0.95, rate(workflow_latency_ms_bucket[5m]))
```
- **Visualization**: Graph
- **Title**: "P95 Workflow Latency (ms)"

**Panel 4: Agent Invocations**
```promql
sum(rate(agent_PlannerAgent_invocations_total[5m])) by (agent)
```
- **Visualization**: Graph
- **Title**: "Agent Invocations per Second"
- **Legend**: `{{agent}}`

**Panel 5: LLM Cost**
```promql
sum(llm_cost_total)
```
- **Visualization**: Stat
- **Title**: "Total LLM Cost (USD)"
- **Unit**: Currency USD

**Panel 6: Policy Violations**
```promql
sum(rate(policy_violations_total[5m]))
```
- **Visualization**: Graph
- **Title**: "Policy Violations per Second"

#### B. Pre-built Dashboards

**Import JSON dashboards** (if available):
- Configuration → Dashboards → Import
- Upload JSON file or paste dashboard JSON

---

## 4. Kibana (Logs) 📝

**URL**: http://localhost:5601

### How to Generate Logs

**Logs are automatically generated when you run a workflow**:
```bash
python3 main.py
```

**What gets logged**:
- Application logs (INFO, WARNING, ERROR)
- `[AUDIT]` entries for agent input/output
- `[POLICY]` entries for policy decisions
- `[TASK]` entries for task lifecycle

**Note**: For logs to appear in Kibana:
- Application logs must be written to `./logs/*.log` directory
- Filebeat ships logs from `/var/log/taskpilot/*.log` to Elasticsearch
- If running in script mode, logs go to stdout (not Kibana)
- For Kibana, run in server mode or configure logging to files

### Setup

1. **Open Kibana**: http://localhost:5601
2. **Create Index Pattern** (first time only):
   - Management → Stack Management → Index Patterns
   - Create index pattern: `filebeat-*` or `taskpilot-logs-*`
   - Time field: `@timestamp`
   - Click "Create index pattern"

### What to Look For

#### A. Discover View

1. **Go to Discover**: Left sidebar → Discover
2. **Select Index Pattern**: `filebeat-*` or your pattern
3. **View Logs**: All logs appear in timeline

**Key Fields to Look For**:
- `@timestamp`: When the log occurred
- `message`: Log message content
- `level`: `INFO`, `WARNING`, `ERROR`
- `agent_name`: Which agent logged this
- `request_id`: Correlate with traces
- `service.name`: Should be `taskpilot`

#### B. Search & Filter

**Example Searches**:

1. **Find all errors**:
   ```
   level:ERROR
   ```

2. **Find logs for specific request**:
   ```
   request_id:"1c08e2a2-236c-4dcd-a889-4dc4dde669d7"
   ```

3. **Find PlannerAgent logs**:
   ```
   agent_name:PlannerAgent
   ```

4. **Find policy decisions**:
   ```
   message:"[POLICY]"
   ```

5. **Find audit logs**:
   ```
   message:"[AUDIT]"
   ```

#### C. Create Visualizations

**1. Error Rate Over Time**:
- Visualize → Create visualization
- Choose "Line" chart
- Y-axis: Count of documents
- X-axis: `@timestamp` (histogram)
- Filter: `level:ERROR`

**2. Logs by Agent**:
- Choose "Pie" chart
- Slice by: `agent_name.keyword`
- Filter: `service.name:taskpilot`

**3. Logs by Level**:
- Choose "Bar" chart
- X-axis: `level.keyword`
- Y-axis: Count

#### D. Create Dashboard

1. **Dashboard → Create Dashboard**
2. **Add saved visualizations**
3. **Arrange panels**
4. **Save dashboard**

---

## 5. Policy Decisions (Decision Logs) 🛡️

**Location**: `decision_logs.jsonl` (local file)

### How to Generate

**Policy decisions are automatically generated when you run a workflow**:
```bash
python3 main.py
```

Each tool call triggers a policy decision that is logged.

### What to Look For

#### A. View Decision Logs

```bash
# View latest decisions
tail -20 decision_logs.jsonl | python3 -m json.tool

# Count total decisions
wc -l decision_logs.jsonl

# Find specific decision type
grep '"decision_type":"tool_call"' decision_logs.jsonl | tail -5

# Find denied decisions
grep '"result":"deny"' decision_logs.jsonl | tail -5
```

#### B. Decision Log Structure

Each line is a JSON object:

```json
{
  "decision_id": "uuid",
  "timestamp": "2025-12-23T15:16:12.123456",
  "decision_type": "tool_call",
  "result": "allow" | "deny" | "require_approval",
  "reason": "Allowed" | "Policy violation: ...",
  "context": {
    "tool_name": "create_task",
    "parameters": {...},
    "agent_type": "PlannerAgent"
  },
  "agent_id": "PlannerAgent",
  "tool_name": "create_task",
  "latency_ms": 0.123
}
```

#### C. Analyze Decisions

**1. Decision Summary**:
```bash
# Count by result
grep -o '"result":"[^"]*"' decision_logs.jsonl | sort | uniq -c

# Count by decision type
grep -o '"decision_type":"[^"]*"' decision_logs.jsonl | sort | uniq -c

# Count by agent
grep -o '"agent_id":"[^"]*"' decision_logs.jsonl | sort | uniq -c
```

**2. Find Violations**:
```bash
# All denied decisions
grep '"result":"deny"' decision_logs.jsonl | python3 -m json.tool

# Decisions requiring approval
grep '"result":"require_approval"' decision_logs.jsonl | python3 -m json.tool
```

**3. Performance Analysis**:
```bash
# Average decision latency
cat decision_logs.jsonl | python3 -c "
import sys, json
latencies = [json.loads(line)['latency_ms'] for line in sys.stdin if 'latency_ms' in line]
if latencies:
    print(f'Avg: {sum(latencies)/len(latencies):.3f}ms')
    print(f'Min: {min(latencies):.3f}ms')
    print(f'Max: {max(latencies):.3f}ms')
"
```

---

## 6. Quick Reference 🚀

### Complete Run Instructions

**To generate all data and check tools**:

```bash
# 1. Start Docker services
docker-compose -f docker-compose.observability.yml up -d

# 2. Activate venv
source .venv/bin/activate

# 3. Run workflow (generates traces, metrics, logs, decisions)
python3 main.py

# 4. Wait 2-3 seconds for data export

# 5. Check each tool:
#    - Jaeger: http://localhost:16686
#    - Prometheus: http://localhost:9090
#    - Grafana: http://localhost:3000
#    - Kibana: http://localhost:5601
#    - Decisions: tail decision_logs.jsonl | python3 -m json.tool
```

**For detailed instructions**: See `GENERATE_DATA_FOR_TOOLS.md`

### Service URLs

| Tool | URL | Purpose |
|------|-----|---------|
| **Jaeger** | http://localhost:16686 | Distributed tracing |
| **Prometheus** | http://localhost:9090 | Metrics storage & query |
| **Grafana** | http://localhost:3000 | Metrics visualization |
| **Kibana** | http://localhost:5601 | Log visualization |
| **Elasticsearch** | http://localhost:9200 | Log storage (API) |
| **TaskPilot API** | http://localhost:8000 | Application endpoints |

### Common Queries

#### Jaeger
- **Service**: `taskpilot`
- **Operation**: `taskpilot.workflow.run`
- **Tag**: `request.id=<id>`

#### Prometheus
- **Workflow runs**: `sum(workflow_runs_total)`
- **Success rate**: `sum(workflow_success_total) / sum(workflow_runs_total) * 100`
- **P95 latency**: `histogram_quantile(0.95, rate(workflow_latency_ms_bucket[5m]))`

#### Kibana
- **Errors**: `level:ERROR`
- **By request**: `request_id:"<id>"`
- **By agent**: `agent_name:PlannerAgent`

### Key Metrics to Monitor

1. **Golden Signals**:
   - Success rate (should be > 95%)
   - P95 latency (should be < 5 seconds)
   - Error rate (should be < 1%)
   - Cost per successful task

2. **Agent Performance**:
   - Invocation count per agent
   - Success/error rates per agent
   - Latency per agent

3. **Policy Compliance**:
   - Total violations
   - Violation rate
   - Decisions requiring approval

4. **Cost Tracking**:
   - Total LLM cost
   - Cost per workflow
   - Token usage (input/output)

---

## Troubleshooting

### No Traces in Jaeger
- ✅ **Check OTEL Collector**: `docker ps | grep otel`
- ✅ **Check OTEL endpoint**: `http://localhost:4317`
- ✅ **Verify workflow ran**: Check stdout for "Workflow completed"
- ✅ **Wait longer**: Traces export asynchronously (2-5 seconds)

**Fix**:
```bash
docker restart taskpilot-otel-collector
docker logs taskpilot-otel-collector
```

### No Metrics in Prometheus
- ✅ **Check `/metrics` endpoint**: `curl http://localhost:8000/metrics` (if server mode)
- ✅ **Verify Prometheus is scraping**: http://localhost:9090/targets
- ✅ **Run workflow**: Metrics generated during execution

**Fix**:
```bash
# Run workflow to generate metrics
python3 main.py

# OR run in server mode for continuous metrics
python3 main.py --server --port 8000
```

### No Logs in Kibana
- ✅ **Check Filebeat**: `docker ps | grep filebeat`
- ✅ **Check Elasticsearch**: `curl http://localhost:9200/_cat/indices`
- ✅ **Verify log files exist**: `ls -la logs/*.log`

**Note**: Logs in Kibana require:
- Application logs written to `./logs/*.log` directory
- Filebeat shipping them to Elasticsearch
- If running in script mode, logs go to stdout (not Kibana)

**Fix**:
```bash
# Check Filebeat logs
docker logs taskpilot-filebeat

# Restart Filebeat
docker restart taskpilot-filebeat
```

### Missing Hierarchy in Jaeger
- ✅ **Verify global tracer is set**: Check `setup_observability()` was called
- ✅ **Check parent_span_id is passed correctly**: Verify middleware code
- ✅ **Ensure all spans use same tracer instance**: Fixed in latest code

**Status**: ✅ Hierarchy fix applied - should work now!

### No Policy Decisions
- ✅ **Check file exists**: `ls -lh decision_logs.jsonl`
- ✅ **Verify workflow ran**: Decisions generated during tool calls
- ✅ **Check policy enabled**: `setup_observability(enable_policy=True)`

**Fix**:
```bash
# Run workflow
python3 main.py

# Check file
tail decision_logs.jsonl | python3 -m json.tool
```

---

## Next Steps

1. ✅ **Start services**: `docker-compose -f docker-compose.observability.yml up -d`
2. ✅ **Run workflow**: `python3 main.py`
3. ✅ **Wait 2-3 seconds**: For data export
4. ✅ **Check Jaeger**: http://localhost:16686 - Verify hierarchy
5. ✅ **Check Prometheus**: http://localhost:9090 - Query metrics
6. ✅ **Check Kibana**: http://localhost:5601 - View logs (if available)
7. ✅ **Check Grafana**: http://localhost:3000 - Create dashboards
8. ✅ **Review decisions**: `tail decision_logs.jsonl | python3 -m json.tool`

**For complete run instructions**: See `GENERATE_DATA_FOR_TOOLS.md`

**Status**: ✅ All tools ready to use!
