# Metrics Demo Scenarios

**Purpose:** This document outlines different scenarios to demonstrate the value of automatically-enabled observability metrics in Docker tools (Prometheus, Grafana, Jaeger, Kibana). Use these scenarios for leadership demos, team training, or showcasing ROI.

**Tools:** Prometheus, Grafana, Jaeger, Kibana  
**Metrics:** All automatically enabled via `agent-observable-core`

---

## Table of Contents

1. [Cost Optimization Scenarios](#cost-optimization-scenarios)
2. [Performance Optimization Scenarios](#performance-optimization-scenarios)
3. [Reliability & Quality Scenarios](#reliability--quality-scenarios)
4. [Security & Compliance Scenarios](#security--compliance-scenarios)
5. [Debugging & Troubleshooting Scenarios](#debugging--troubleshooting-scenarios)
6. [Business Intelligence Scenarios](#business-intelligence-scenarios)
7. [Multi-Agent Workflow Scenarios](#multi-agent-workflow-scenarios)

---

## Cost Optimization Scenarios

### Scenario 1: Model Cost Comparison

**Business Value:** Identify cost savings by comparing model usage and costs.

**Setup:**
1. Run workflows using different models (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
2. Track costs over time

**Metrics to Show:**
- `llm_cost_total` - Total cost
- `llm_cost_model.{model}` - Cost per model
- `llm_tokens_total.{model}` - Tokens per model
- `cost_per_successful_task` (Golden Signal)

**Grafana Dashboard:**
- **Panel 1:** Cost by Model (bar chart)
  - Query: `llm_cost_model_gpt_4o`, `llm_cost_model_gpt_4o_mini`, `llm_cost_model_gpt_3_5_turbo`
- **Panel 2:** Cost per 1K Tokens by Model
  - Query: `llm_cost_model_gpt_4o / (llm_tokens_total_gpt_4o / 1000)`
- **Panel 3:** Cost Trend Over Time (line chart)
  - Query: `rate(llm_cost_total[5m])`

**Demo Script:**
```
"Here we can see that gpt-4o-mini costs 80% less than gpt-4o while 
maintaining similar quality. By switching PlannerAgent to gpt-4o-mini, 
we could save $X per month."
```

**Expected Insight:** Identify opportunities to use cheaper models without quality degradation.

---

### Scenario 2: Agent Cost Analysis

**Business Value:** Understand which agents consume the most budget.

**Setup:**
1. Run multi-agent workflows (PlannerAgent, ExecutorAgent, ReviewerAgent)
2. Track costs per agent

**Metrics to Show:**
- `llm_cost_agent.{name}` - Cost per agent
- `agent.{name}.invocations` - Invocations per agent
- `agent.{name}.latency_ms_p95` - Latency per agent

**Grafana Dashboard:**
- **Panel 1:** Cost by Agent (pie chart)
  - Query: `llm_cost_agent_PlannerAgent`, `llm_cost_agent_ExecutorAgent`, `llm_cost_agent_ReviewerAgent`
- **Panel 2:** Cost per Invocation by Agent
  - Query: `llm_cost_agent_PlannerAgent / agent_PlannerAgent_invocations`
- **Panel 3:** Agent Efficiency (cost vs. latency)
  - Scatter plot: X-axis = latency, Y-axis = cost

**Demo Script:**
```
"PlannerAgent accounts for 60% of our LLM costs. By optimizing its 
prompts to reduce token usage, we could reduce costs by 30% while 
maintaining the same functionality."
```

**Expected Insight:** Identify high-cost agents for optimization.

---

### Scenario 3: Token Usage Optimization

**Business Value:** Optimize prompts to reduce token consumption.

**Setup:**
1. Track token usage before and after prompt optimization
2. Compare input vs. output tokens

**Metrics to Show:**
- `llm_tokens_input_total` - Total input tokens
- `llm_tokens_output_total` - Total output tokens
- `llm_tokens_input.{model}` - Input tokens per model
- `llm_tokens_output.{model}` - Output tokens per model

**Grafana Dashboard:**
- **Panel 1:** Token Usage Trend (stacked area chart)
  - Query: `rate(llm_tokens_input_total[5m])`, `rate(llm_tokens_output_total[5m])`
- **Panel 2:** Input/Output Ratio
  - Query: `llm_tokens_output_total / llm_tokens_input_total`
- **Panel 3:** Average Tokens per Workflow
  - Query: `llm_tokens_total_all / workflow_runs`

**Demo Script:**
```
"After optimizing prompts, we reduced input tokens by 40% and output 
tokens by 25%, resulting in a 35% cost reduction per workflow."
```

**Expected Insight:** Identify token waste and optimization opportunities.

---

### Scenario 4: Cost Anomaly Detection

**Business Value:** Detect unexpected cost spikes early.

**Setup:**
1. Set up alerts for cost thresholds
2. Monitor cost trends

**Metrics to Show:**
- `llm_cost_total` - Total cost
- `cost_per_successful_task` (Golden Signal)
- Alert: `HighCostPerTask` (from golden-signals-alerts.yml)

**Grafana Dashboard:**
- **Panel 1:** Cost per Task Over Time (line chart with thresholds)
  - Query: `llm_cost_total / clamp_min(workflow_success, 1)`
  - Thresholds: Green < $0.10, Yellow $0.10-$0.50, Red > $0.50
- **Panel 2:** Cost Spike Detection
  - Query: `increase(llm_cost_total[1h])` - Shows hourly cost increase

**Prometheus Alert:**
```yaml
- alert: HighCostPerTask
  expr: llm_cost_total / workflow_success > 1.0
  for: 5m
```

**Demo Script:**
```
"Our alert system detected a cost spike at 2 PM. Investigation showed 
a bug causing excessive retries. We fixed it within 30 minutes, 
preventing $X in additional costs."
```

**Expected Insight:** Early detection of cost anomalies prevents budget overruns.

---

## Performance Optimization Scenarios

### Scenario 5: Latency Bottleneck Identification

**Business Value:** Identify performance bottlenecks in multi-agent workflows.

**Setup:**
1. Run workflows with multiple agents
2. Track latency per agent

**Metrics to Show:**
- `agent.{name}.latency_ms_p95` - P95 latency per agent
- `workflow.latency_ms_p95` - Overall workflow latency
- `tool.{name}.latency_ms_p95` - Tool latency

**Grafana Dashboard:**
- **Panel 1:** Agent Latency Comparison (bar chart)
  - Query: `agent_PlannerAgent_latency_ms_p95`, `agent_ExecutorAgent_latency_ms_p95`
- **Panel 2:** Latency Breakdown (waterfall chart in Jaeger)
  - Show: Workflow → Agent → Tool hierarchy
- **Panel 3:** Latency Trend Over Time
  - Query: `workflow_latency_ms_p95`

**Jaeger Visualization:**
- Select a slow trace
- Show timeline: "PlannerAgent takes 2s, ExecutorAgent takes 5s"
- Identify: "ExecutorAgent is the bottleneck"

**Demo Script:**
```
"Jaeger shows that ExecutorAgent accounts for 70% of workflow latency. 
By optimizing its tool calls or using parallel execution, we could 
reduce total workflow time by 50%."
```

**Expected Insight:** Identify agents/tools causing performance issues.

---

### Scenario 6: Success Rate Monitoring

**Business Value:** Monitor system reliability and quality.

**Setup:**
1. Run workflows and track success/failure rates
2. Monitor trends over time

**Metrics to Show:**
- `workflow_runs` - Total runs
- `workflow_success` - Successful runs
- `workflow_errors` - Failed runs
- `success_rate` (Golden Signal)

**Grafana Dashboard:**
- **Panel 1:** Success Rate Over Time (line chart with thresholds)
  - Query: `(workflow_success / workflow_runs) * 100`
  - Thresholds: Green ≥ 95%, Yellow ≥ 90%, Red < 90%
- **Panel 2:** Error Rate Trend
  - Query: `(workflow_errors / workflow_runs) * 100`
- **Panel 3:** Success vs. Errors (stacked area chart)
  - Query: `rate(workflow_success[5m])`, `rate(workflow_errors[5m])`

**Prometheus Alert:**
```yaml
- alert: LowSuccessRate
  expr: (workflow_success / workflow_runs) * 100 < 90
  for: 5m
```

**Demo Script:**
```
"Our success rate dropped from 98% to 85% at 3 PM. The alert triggered, 
and we identified a new agent configuration causing failures. We rolled 
back within 10 minutes, restoring 98% success rate."
```

**Expected Insight:** Early detection of quality degradation.

---

### Scenario 7: Tool Performance Analysis

**Business Value:** Identify slow or unreliable tools.

**Setup:**
1. Track tool call metrics
2. Compare tool performance

**Metrics to Show:**
- `tool.{name}.calls` - Tool invocations
- `tool.{name}.success` - Successful calls
- `tool.{name}.errors` - Failed calls
- `tool.{name}.latency_ms_p95` - Tool latency

**Grafana Dashboard:**
- **Panel 1:** Tool Success Rate
  - Query: `(tool_create_task_success / tool_create_task_calls) * 100`
- **Panel 2:** Tool Latency Comparison
  - Query: `tool_create_task_latency_ms_p95`, `tool_update_task_latency_ms_p95`
- **Panel 3:** Tool Error Rate
  - Query: `(tool_create_task_errors / tool_create_task_calls) * 100`

**Demo Script:**
```
"Tool 'update_task' has a 15% error rate and 2s latency, compared to 
other tools with <1% error rate and <200ms latency. This indicates 
a problem with the external API we're calling."
```

**Expected Insight:** Identify problematic external dependencies.

---

## Reliability & Quality Scenarios

### Scenario 8: Retry Effectiveness Analysis

**Business Value:** Understand retry patterns and optimize retry logic.

**Setup:**
1. Enable retry logic with exponential backoff
2. Track retry metrics

**Metrics to Show:**
- `retry.attempts` - Total retry attempts
- `retry.success_after_attempts` - Successful retries
- `retry.exhausted` - Exhausted retries

**Grafana Dashboard:**
- **Panel 1:** Retry Success Rate
  - Query: `(retry_success_after_attempts / retry_attempts) * 100`
- **Panel 2:** Retry Exhaustion Rate
  - Query: `(retry_exhausted / retry_attempts) * 100`
- **Panel 3:** Retry Attempts Distribution
  - Histogram: How many attempts before success

**Demo Script:**
```
"80% of retries succeed after 1-2 attempts, but 5% exhaust all retries. 
This suggests transient network issues. We could increase max retries 
for specific error types to improve success rate."
```

**Expected Insight:** Optimize retry configuration for better reliability.

---

### Scenario 9: Guardrails Effectiveness

**Business Value:** Demonstrate safety and content filtering.

**Setup:**
1. Enable NeMo Guardrails
2. Track guardrails blocks

**Metrics to Show:**
- `agent.{name}.guardrails.blocked` - Input blocks
- `agent.{name}.guardrails.output_blocked` - Output blocks

**Grafana Dashboard:**
- **Panel 1:** Guardrails Blocks Over Time
  - Query: `rate(agent_PlannerAgent_guardrails_blocked[5m])`
- **Panel 2:** Block Rate by Agent
  - Query: `agent_PlannerAgent_guardrails_blocked / agent_PlannerAgent_invocations * 100`

**Kibana Visualization:**
- Search: `decision_type:guardrails AND result:deny`
- Show: Blocked content examples (anonymized)
- Timeline: When blocks occurred

**Demo Script:**
```
"Our guardrails blocked 12 potentially harmful requests this week, 
preventing inappropriate content from being processed. This demonstrates 
our commitment to safety and compliance."
```

**Expected Insight:** Demonstrate proactive safety measures.

---

## Security & Compliance Scenarios

### Scenario 10: Policy Violation Tracking

**Business Value:** Demonstrate compliance and security posture.

**Setup:**
1. Enable OPA policy validation
2. Track policy violations

**Metrics to Show:**
- `policy.violations.total` - Total violations
- `agent.{name}.policy.violations` - Violations per agent
- `policy_violation_rate` (Golden Signal)

**Grafana Dashboard:**
- **Panel 1:** Policy Violation Rate Over Time
  - Query: `(policy_violations_total / workflow_runs) * 100`
  - Thresholds: Green < 1%, Yellow < 2%, Red ≥ 2%
- **Panel 2:** Violations by Agent
  - Query: `agent_PlannerAgent_policy_violations`, `agent_ExecutorAgent_policy_violations`

**Kibana Visualization:**
- Search: `decision_type:opa AND result:deny`
- Show: Policy decisions with context
- Filter: By agent, tool, policy name

**Prometheus Alert:**
```yaml
- alert: HighViolationRate
  expr: (policy_violations_total / workflow_runs) * 100 > 5
  for: 5m
```

**Demo Script:**
```
"Our policy engine blocked 3 unauthorized tool access attempts this 
month. All violations are logged with full context for audit purposes, 
demonstrating our security controls are working."
```

**Expected Insight:** Demonstrate security and compliance posture.

---

### Scenario 11: Audit Trail for Compliance

**Business Value:** Complete audit trail for regulatory compliance.

**Setup:**
1. Enable policy decision logging
2. View decisions in Kibana

**Data to Show:**
- Policy decisions (JSONL format)
- Tool call validations
- OPA decisions
- Human review decisions

**Kibana Dashboard:**
- **Panel 1:** Decision Timeline
  - X-axis: Time
  - Y-axis: Decision type (tool_call, opa, guardrails, human_review)
  - Color: Result (allow=green, deny=red, requires_approval=yellow)
- **Panel 2:** Decisions by Type
  - Pie chart: tool_call, opa, guardrails, human_review
- **Panel 3:** Denied Decisions Table
  - Columns: timestamp, decision_type, tool_name, agent_id, reason

**Demo Script:**
```
"For compliance, we maintain a complete audit trail of all policy 
decisions. Here we can see every tool call validation, OPA decision, 
and guardrails check with full context. This satisfies our regulatory 
requirements."
```

**Expected Insight:** Demonstrate compliance readiness.

---

## Debugging & Troubleshooting Scenarios

### Scenario 12: End-to-End Request Tracing

**Business Value:** Quickly debug issues by following request flow.

**Setup:**
1. Run workflows with errors
2. View traces in Jaeger

**Traces to Show:**
- Workflow span with request ID
- Agent spans (child of workflow)
- Tool spans (child of agent)
- Error spans with error details

**Jaeger Visualization:**
1. **Find Failed Request:**
   - Filter: `error=true`
   - Select a trace with error
2. **View Hierarchy:**
   - Workflow → PlannerAgent → create_task (failed)
   - Click on failed span to see error message
3. **Correlate with Logs:**
   - Use request ID to find logs in Kibana
   - Search: `request.id:abc123`

**Demo Script:**
```
"A user reported an error. We found the request ID in logs, then 
traced it in Jaeger. The trace shows the error occurred in 
'create_task' tool call. We can see the exact error message and 
context, allowing us to fix it quickly."
```

**Expected Insight:** Reduce mean time to resolution (MTTR).

---

### Scenario 13: Error Pattern Analysis

**Business Value:** Identify common error patterns and root causes.

**Setup:**
1. Track errors over time
2. Analyze error patterns

**Metrics to Show:**
- `workflow_errors` - Workflow errors
- `agent.{name}.errors` - Agent errors
- `tool.{name}.errors` - Tool errors

**Grafana Dashboard:**
- **Panel 1:** Error Rate by Agent
  - Query: `(agent_PlannerAgent_errors / agent_PlannerAgent_invocations) * 100`
- **Panel 2:** Error Rate Trend
  - Query: `rate(workflow_errors[5m])`
- **Panel 3:** Error Distribution
  - Pie chart: Errors by agent

**Kibana Visualization:**
- Search: `level:ERROR`
- Group by: `error.code` or `error.type`
- Timeline: When errors occurred
- Show: Most common error codes

**Demo Script:**
```
"Error analysis shows that 60% of errors are 'TOOL_TIMEOUT' errors 
from 'update_task' tool. This suggests the external API is unreliable. 
We should implement better retry logic or find an alternative API."
```

**Expected Insight:** Identify systemic issues and root causes.

---

### Scenario 14: Performance Regression Detection

**Business Value:** Detect performance regressions before they impact users.

**Setup:**
1. Monitor latency trends
2. Set up alerts for latency spikes

**Metrics to Show:**
- `workflow_latency_ms_p95` - P95 latency
- `agent.{name}.latency_ms_p95` - Agent latency
- `p95_latency` (Golden Signal)

**Grafana Dashboard:**
- **Panel 1:** Latency Trend Over Time
  - Query: `workflow_latency_ms_p95`
  - Annotations: Deployments, code changes
- **Panel 2:** Latency by Agent
  - Query: `agent_PlannerAgent_latency_ms_p95`, `agent_ExecutorAgent_latency_ms_p95`
- **Panel 3:** Latency Distribution
  - Histogram: P50, P95, P99 latencies

**Prometheus Alert:**
```yaml
- alert: HighLatency
  expr: workflow_latency_ms_p95 > 10000
  for: 5m
```

**Demo Script:**
```
"After deploying version 2.0, we noticed latency increased from 2s 
to 5s. The alert triggered, and we identified the new feature causing 
the slowdown. We rolled back and fixed the issue before users were 
impacted."
```

**Expected Insight:** Proactive performance monitoring.

---

## Business Intelligence Scenarios

### Scenario 15: Workflow Volume & Growth

**Business Value:** Track business metrics and growth.

**Setup:**
1. Monitor workflow execution volume
2. Track growth trends

**Metrics to Show:**
- `workflow_runs` - Total workflow executions
- `workflow_success` - Successful executions
- Rate of change over time

**Grafana Dashboard:**
- **Panel 1:** Workflow Volume Over Time
  - Query: `rate(workflow_runs[5m]) * 60 * 60` (workflows per hour)
- **Panel 2:** Daily Workflow Count
  - Query: `increase(workflow_runs[1d])`
- **Panel 3:** Growth Rate
  - Query: `(increase(workflow_runs[7d]) - increase(workflow_runs[7d] offset 7d)) / increase(workflow_runs[7d] offset 7d) * 100`

**Demo Script:**
```
"Our workflow volume has grown 25% month-over-month. We're processing 
10,000 workflows per day, with 98% success rate. This demonstrates 
strong adoption and reliability."
```

**Expected Insight:** Business growth and adoption metrics.

---

### Scenario 16: Cost Efficiency Over Time

**Business Value:** Demonstrate cost optimization improvements.

**Setup:**
1. Track cost per task over time
2. Show improvements after optimizations

**Metrics to Show:**
- `cost_per_successful_task` (Golden Signal)
- `llm_cost_total` - Total cost
- `workflow_success` - Successful workflows

**Grafana Dashboard:**
- **Panel 1:** Cost per Task Trend
  - Query: `llm_cost_total / clamp_min(workflow_success, 1)`
  - Annotations: Optimization milestones
- **Panel 2:** Total Cost vs. Volume
  - Dual Y-axis: Cost (left), Volume (right)
- **Panel 3:** Cost Efficiency Score
  - Query: `workflow_success / llm_cost_total` (workflows per dollar)

**Demo Script:**
```
"After implementing prompt optimization and model switching, we reduced 
cost per task from $0.15 to $0.08, a 47% reduction. With 10,000 tasks 
per day, this saves $2,100 per month."
```

**Expected Insight:** Demonstrate ROI of optimizations.

---

### Scenario 17: Agent Utilization Analysis

**Business Value:** Understand agent usage patterns.

**Setup:**
1. Track agent invocations
2. Compare agent usage

**Metrics to Show:**
- `agent.{name}.invocations` - Agent invocations
- `agent.{name}.success` - Successful invocations
- `agent.{name}.latency_ms_p95` - Agent latency

**Grafana Dashboard:**
- **Panel 1:** Agent Invocation Distribution
  - Pie chart: Invocations by agent
- **Panel 2:** Agent Utilization Over Time
  - Stacked area chart: Invocations per agent over time
- **Panel 3:** Agent Efficiency Matrix
  - Scatter plot: X = latency, Y = success rate, Size = invocations

**Demo Script:**
```
"PlannerAgent is used in 80% of workflows, while ReviewerAgent is 
only used in 20%. This suggests we could optimize workflows to reduce 
unnecessary reviews, improving efficiency."
```

**Expected Insight:** Optimize workflow design based on usage patterns.

---

## Multi-Agent Workflow Scenarios

### Scenario 18: Workflow Composition Analysis

**Business Value:** Understand how agents work together in workflows.

**Setup:**
1. Run multi-agent workflows
2. View traces showing agent interactions

**Traces to Show:**
- Workflow span (parent)
  - PlannerAgent span (child)
    - Tool spans (grandchildren)
  - ExecutorAgent span (child)
    - Tool spans (grandchildren)
  - ReviewerAgent span (child)

**Jaeger Visualization:**
1. **Select a Workflow Trace:**
   - Filter: `operationName:taskpilot.workflow.run`
   - Select a trace
2. **View Timeline:**
   - See sequential vs. parallel agent execution
   - Identify wait times between agents
3. **Analyze Dependencies:**
   - Which agents depend on others
   - Where parallelization is possible

**Grafana Dashboard:**
- **Panel 1:** Agent Execution Order
  - Timeline showing agent start/end times
- **Panel 2:** Inter-Agent Wait Time
  - Time between agent completions

**Demo Script:**
```
"Trace analysis shows that ExecutorAgent waits 500ms after PlannerAgent 
completes. By optimizing the handoff or running agents in parallel 
where possible, we could reduce total workflow time by 30%."
```

**Expected Insight:** Optimize workflow design for better performance.

---

### Scenario 19: Agent Failure Impact Analysis

**Business Value:** Understand cascading failures in multi-agent workflows.

**Setup:**
1. Introduce failures in specific agents
2. Track impact on overall workflow

**Metrics to Show:**
- `agent.{name}.errors` - Agent errors
- `workflow_errors` - Workflow errors
- Error correlation

**Jaeger Visualization:**
1. **Find Failed Workflow:**
   - Filter: `error=true`
   - Select trace
2. **Identify Failure Point:**
   - Which agent failed first
   - Did other agents still execute?
   - What was the error?
3. **View Error Propagation:**
   - Did failure cascade to other agents?
   - Which agents handled errors gracefully?

**Grafana Dashboard:**
- **Panel 1:** Agent Error Rate vs. Workflow Error Rate
  - Correlation: When agent errors increase, do workflow errors increase?
- **Panel 2:** Failure Cascade Analysis
  - When Agent X fails, what % of workflows fail?

**Demo Script:**
```
"When PlannerAgent fails, 90% of workflows fail. But when ExecutorAgent 
fails, only 10% of workflows fail because ReviewerAgent can still 
complete. This shows we need better error handling in PlannerAgent."
```

**Expected Insight:** Identify critical failure points and improve resilience.

---

## Demo Preparation Checklist

### Before Demo

- [ ] Start Docker services: `docker-compose -f docker-compose.observability.yml up -d`
- [ ] Start application server: `python main.py --server --port 8000`
- [ ] Run test workflows to generate data
- [ ] Verify metrics in Prometheus: http://localhost:9090
- [ ] Verify traces in Jaeger: http://localhost:16686
- [ ] Verify logs in Kibana: http://localhost:5601
- [ ] Import Grafana dashboard: `golden-signals-dashboard.json`
- [ ] Set appropriate time ranges (last 6 hours, last 24 hours, etc.)

### Demo Flow

1. **Start with Golden Signals Dashboard** (Grafana)
   - Show high-level health indicators
   - Explain what each signal means

2. **Drill Down into Specific Metrics** (Grafana)
   - Cost analysis
   - Performance analysis
   - Reliability metrics

3. **Show Traces** (Jaeger)
   - Pick a specific request
   - Show end-to-end flow
   - Demonstrate debugging capability

4. **Show Policy Decisions** (Kibana)
   - Security/compliance demonstration
   - Audit trail

5. **Show Alerts** (Prometheus/Grafana)
   - Alert rules
   - Alert history

### Key Talking Points

- **Zero Configuration:** "All this observability is automatic - no manual instrumentation"
- **Framework-Agnostic:** "Works with any agent framework"
- **Business Value:** "This helps us optimize costs, improve reliability, and ensure compliance"
- **Actionable Insights:** "We can identify issues quickly and make data-driven decisions"

---

## Scenario Summary Table

| Scenario | Primary Tool | Key Metrics | Business Value |
|----------|--------------|-------------|----------------|
| Model Cost Comparison | Grafana | `llm_cost_model.*` | Cost savings |
| Agent Cost Analysis | Grafana | `llm_cost_agent.*` | Budget allocation |
| Token Usage Optimization | Grafana | `llm_tokens_*` | Cost reduction |
| Cost Anomaly Detection | Grafana + Alerts | `llm_cost_total` | Budget protection |
| Latency Bottleneck | Jaeger + Grafana | `agent.*.latency_ms_p95` | Performance |
| Success Rate Monitoring | Grafana + Alerts | `success_rate` | Reliability |
| Tool Performance | Grafana | `tool.*.latency_ms_p95` | Dependency health |
| Retry Effectiveness | Grafana | `retry.*` | Resilience |
| Guardrails Effectiveness | Grafana + Kibana | `agent.*.guardrails.*` | Safety |
| Policy Violation Tracking | Grafana + Kibana | `policy.violations.*` | Compliance |
| Audit Trail | Kibana | Policy decisions | Compliance |
| End-to-End Tracing | Jaeger | Traces | Debugging |
| Error Pattern Analysis | Grafana + Kibana | `*_errors` | Root cause |
| Performance Regression | Grafana + Alerts | `*_latency_ms_p95` | Proactive monitoring |
| Workflow Volume | Grafana | `workflow_runs` | Business metrics |
| Cost Efficiency | Grafana | `cost_per_successful_task` | ROI |
| Agent Utilization | Grafana | `agent.*.invocations` | Optimization |
| Workflow Composition | Jaeger | Traces | Design optimization |
| Failure Impact | Jaeger + Grafana | Error correlation | Resilience |

---

## Next Steps

1. **Prepare Demo Data:** Run workflows to generate realistic data
2. **Create Custom Dashboards:** Build scenario-specific Grafana dashboards
3. **Set Up Alerts:** Configure Prometheus alerts for key scenarios
4. **Document Findings:** Create reports showing insights from each scenario
5. **Train Team:** Use scenarios for team training on observability tools
