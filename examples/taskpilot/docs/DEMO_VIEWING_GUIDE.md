# Demo Data Viewing Guide

**Status:** ✅ Demo data has been generated and verified in Docker tools.

**Generated Data:**
- ✅ **350 log entries** in `logs/taskpilot.log` (shipped to Elasticsearch)
- ✅ **30 policy decisions** in `decision_logs.jsonl`
- ✅ **50 traces** in Jaeger (10 per scenario)
- ✅ **296 documents** in Elasticsearch (from Filebeat)

**Scenarios Generated:**
1. Cost Optimization (model comparison)
2. Performance Bottleneck (slow ExecutorAgent)
3. Policy Violations (denied decisions)
4. Error Patterns (various error types)

---

## Quick Start

1. **All services are running** ✅
2. **Data is generated** ✅
3. **Filebeat has shipped logs** ✅

**View data in these tools:**

---

## 1. Grafana (Metrics & Dashboards)

**URL:** http://localhost:3000  
**Login:** `admin` / `admin`

### Dashboard: Golden Signals LLM Production

**Direct Link:** http://localhost:3000/d/02b9018d-c9b7-4b7d-8b09-1bc4fdfccba8/golden-signals-llm-production

**What to Check:**

1. **Cost per Successful Task**
   - Panel: "Cost per Successful Task"
   - Should show cost metrics (may be 0 if metrics server not running)
   - **Note:** Metrics are in-memory. Start server to see: `python main.py --server --port 8000`

2. **Workflow Success Rate**
   - Panel: "Workflow Success Rate"
   - Shows percentage of successful workflows

3. **Policy Violations**
   - Panel: "Policy Violations Rate"
   - Shows policy violation metrics

4. **Agent Latency (P95)**
   - Panel: "Agent Latency P95"
   - Should show ExecutorAgent with high latency (5000ms+) in performance_bottleneck scenario

### Custom Queries to Try

Go to **Explore** (compass icon) and try:

```
# Workflow metrics
workflow_runs
workflow_success
workflow_errors

# LLM cost metrics
llm_cost_total
llm_cost_model_gpt_4o
llm_cost_model_gpt_4o_mini

# Policy metrics
policy_violations_total

# Agent latency
agent_PlannerAgent_latency_ms_p95
agent_ExecutorAgent_latency_ms_p95
```

**Screenshot Suggestions:**
- Dashboard overview showing all panels
- Cost comparison chart (gpt-4o vs gpt-4o-mini)
- Agent latency comparison (showing slow ExecutorAgent)

---

## 2. Prometheus (Metrics Query)

**URL:** http://localhost:9090

### Queries to Try

1. **Workflow Metrics:**
   ```
   workflow_runs
   workflow_success
   workflow_errors
   rate(workflow_runs[5m])
   ```

2. **LLM Cost Metrics:**
   ```
   llm_cost_total
   llm_cost_model_gpt_4o
   llm_cost_model_gpt_4o_mini
   llm_tokens_total
   ```

3. **Policy Metrics:**
   ```
   policy_violations_total
   policy_violations_tool_call
   policy_violations_opa
   ```

4. **Agent Metrics:**
   ```
   agent_PlannerAgent_invocations
   agent_ExecutorAgent_invocations
   agent_ExecutorAgent_latency_ms_p95
   ```

5. **Error Metrics:**
   ```
   tool_create_task_errors
   tool_update_task_errors
   agent_ExecutorAgent_errors
   ```

**Note:** Metrics may show `0` if the metrics server is not running. Start it with:
```bash
python main.py --server --port 8000
```

Then wait 15 seconds for Prometheus to scrape.

**Screenshot Suggestions:**
- Query results showing workflow_runs
- Cost metrics comparison
- Error rate over time

---

## 3. Jaeger (Traces)

**URL:** http://localhost:16686

### Search Configuration

1. **Service:** `taskpilot`
2. **Operation:** (leave empty to see all)
3. **Tags:** (optional filters)
   - `scenario=cost_optimization`
   - `scenario=performance_bottleneck`
   - `agent_name=ExecutorAgent`
   - `slow=true`

### What to Check

1. **Trace Hierarchy:**
   - Click on any trace
   - Look for parent-child relationships:
     - `taskpilot.workflow.run` (root)
       - `taskpilot.agent.PlannerAgent.run` (child)
         - `taskpilot.tool.create_task.call` (grandchild)
       - `taskpilot.agent.ExecutorAgent.run` (child)
       - `taskpilot.agent.ReviewerAgent.run` (child)

2. **Slow ExecutorAgent:**
   - Filter by: `scenario=performance_bottleneck`
   - Look for ExecutorAgent spans with `latency_ms` > 5000ms
   - Timeline should show ExecutorAgent taking much longer than other agents

3. **Trace Attributes:**
   - Click on any span
   - Check "Tags" section:
     - `request.id` - Request correlation ID
     - `agent_name` - Agent name
     - `tool_name` - Tool name
     - `scenario` - Demo scenario
     - `latency_ms` - Execution latency

4. **Trace Timeline:**
   - Visual timeline showing span durations
   - Parent spans should encompass child spans
   - Slow spans should be visually obvious

**Screenshot Suggestions:**
- Trace list showing multiple traces
- Trace detail view with hierarchy (workflow → agent → tool)
- Timeline view showing slow ExecutorAgent spans
- Tags/attributes panel showing request_id correlation

---

## 4. Kibana (Logs)

**URL:** http://localhost:5601

### Setup (First Time Only)

1. **Create Index Pattern:**
   - Go to **Stack Management** → **Index Patterns**
   - Click **Create index pattern**
   - Pattern: `taskpilot-logs-*`
   - Time field: `@timestamp`
   - Click **Create index pattern**

2. **Verify Data:**
   - Go to **Discover**
   - Should see log entries with timestamps

### Filters to Try

1. **By Scenario:**
   ```
   scenario:cost_optimization
   scenario:performance_bottleneck
   scenario:policy_violations
   scenario:error_patterns
   ```

2. **By Log Level:**
   ```
   level:ERROR
   level:INFO
   level:WARNING
   ```

3. **By Log Type:**
   ```
   log_type:policy_decision
   ```

4. **By Agent:**
   ```
   agent_name:PlannerAgent
   agent_name:ExecutorAgent
   agent_name:ReviewerAgent
   ```

5. **By Error Type:**
   ```
   error_code:TOOL_TIMEOUT
   error_code:TOOL_EXECUTION_ERROR
   error_code:POLICY_VIOLATION
   ```

6. **Policy Decisions:**
   ```
   log_type:policy_decision AND result:deny
   log_type:policy_decision AND decision_type:opa
   ```

### What to Check

1. **Log Entries:**
   - Should see 350+ log entries
   - Each entry has structured JSON fields
   - Timestamps should be recent (within last hour)

2. **Policy Decisions:**
   - Filter: `log_type:policy_decision`
   - Should see 30+ decision entries
   - Check `decision_type` (tool_call, opa, guardrails)
   - Check `result` (allow, deny, require_approval)

3. **Error Logs:**
   - Filter: `level:ERROR`
   - Should see error entries with:
     - `error_code` (TOOL_TIMEOUT, TOOL_EXECUTION_ERROR, POLICY_VIOLATION)
     - `error_type` (ToolTimeoutError, ToolExecutionError, etc.)
     - `error_message`

4. **Request Correlation:**
   - Filter by `request_id` to see all logs for a single request
   - Should see workflow start, agent execution, tool calls, completion

**Screenshot Suggestions:**
- Discover view with filtered logs (by scenario)
- Policy decisions view (log_type:policy_decision)
- Error logs view (level:ERROR)
- Request correlation view (filtered by request_id)

---

## 5. Elasticsearch (Direct API)

**URL:** http://localhost:9200

### Useful Queries

1. **List Indices:**
   ```bash
   curl http://localhost:9200/_cat/indices/taskpilot-logs-*
   ```

2. **Count Documents:**
   ```bash
   curl http://localhost:9200/taskpilot-logs-*/_count
   ```

3. **Sample Document:**
   ```bash
   curl http://localhost:9200/taskpilot-logs-*/_search?size=1&pretty
   ```

4. **Search by Scenario:**
   ```bash
   curl -X POST http://localhost:9200/taskpilot-logs-*/_search?pretty \
     -H 'Content-Type: application/json' \
     -d '{
       "query": {
         "term": {
           "scenario": "cost_optimization"
         }
       }
     }'
   ```

5. **Search Policy Decisions:**
   ```bash
   curl -X POST http://localhost:9200/taskpilot-logs-*/_search?pretty \
     -H 'Content-Type: application/json' \
     -d '{
       "query": {
         "term": {
           "log_type": "policy_decision"
         }
       }
     }'
   ```

---

## Screenshot Checklist

Use this checklist to capture all important views:

### Grafana
- [ ] Dashboard overview (all panels visible)
- [ ] Cost comparison chart (gpt-4o vs gpt-4o-mini)
- [ ] Agent latency comparison (showing slow ExecutorAgent)
- [ ] Policy violations panel

### Prometheus
- [ ] Query results for `workflow_runs`
- [ ] Query results for `llm_cost_total`
- [ ] Query results for `policy_violations_total`
- [ ] Graph view showing metrics over time

### Jaeger
- [ ] Trace list (showing multiple traces)
- [ ] Trace detail with hierarchy (workflow → agent → tool)
- [ ] Timeline view showing slow ExecutorAgent
- [ ] Tags/attributes panel (showing request_id, agent_name, etc.)
- [ ] Filtered view (scenario=performance_bottleneck)

### Kibana
- [ ] Discover view with all logs
- [ ] Filtered by scenario (scenario:cost_optimization)
- [ ] Policy decisions view (log_type:policy_decision)
- [ ] Error logs view (level:ERROR)
- [ ] Request correlation (filtered by request_id)

---

## Troubleshooting

### Metrics Show 0 in Prometheus/Grafana

**Cause:** Metrics are in-memory and need the server running.

**Solution:**
```bash
# Start metrics server
python main.py --server --port 8000

# Wait 15 seconds for Prometheus to scrape
# Then refresh Grafana dashboard
```

### No Traces in Jaeger

**Cause:** Traces may take time to export, or OTEL Collector not receiving.

**Solution:**
1. Check OTEL Collector logs:
   ```bash
   docker logs taskpilot-otel-collector
   ```

2. Verify OTLP endpoint is accessible:
   ```bash
   curl http://localhost:4317
   ```

3. Re-run trace generation:
   ```bash
   python scripts/generate_demo_data.py
   ```

### No Logs in Kibana

**Cause:** Index pattern not created, or Filebeat hasn't shipped logs yet.

**Solution:**
1. Create index pattern: `taskpilot-logs-*`
2. Check Filebeat logs:
   ```bash
   docker logs taskpilot-filebeat
   ```
3. Wait 30-60 seconds for Filebeat to ship logs

### Grafana Dashboard Not Found

**Cause:** Dashboard not imported.

**Solution:**
1. Go to Dashboards → Import
2. Upload: `observability/grafana/golden-signals-dashboard.json`
3. Or use dashboard UID: `02b9018d-c9b7-4b7d-8b09-1bc4fdfccba8`

---

## Data Summary

**Generated Data:**
- **350 log entries** across 4 scenarios
- **30 policy decisions** (mix of allow/deny/require_approval)
- **50 traces** (10 per scenario, with hierarchy)
- **296 documents** in Elasticsearch (from Filebeat)

**Scenarios:**
1. **Cost Optimization:** Model comparison (gpt-4o vs gpt-4o-mini)
2. **Performance Bottleneck:** Slow ExecutorAgent (5000ms+ latency)
3. **Policy Violations:** Denied decisions (tool_call, OPA)
4. **Error Patterns:** Various error types (TOOL_TIMEOUT, TOOL_EXECUTION_ERROR, POLICY_VIOLATION)

**Files:**
- `logs/taskpilot.log` - 350 JSON log entries
- `decision_logs.jsonl` - 30 policy decision entries

---

## Next Steps

1. **Take Screenshots** using the checklist above
2. **Review Data** in each tool to verify it matches expectations
3. **Customize Queries** to explore specific scenarios
4. **Share Results** with your team

**To Regenerate Data:**
```bash
python scripts/generate_demo_data.py
```

**To Verify Data:**
```bash
python scripts/verify_demo_data.py
```

**To Run Complete Demo:**
```bash
./scripts/run_demo.sh
```
