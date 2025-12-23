# Kibana Filters for Policy Decisions

## Quick Filters

### All Policy Decisions
```
log_type: "policy_decision"
```

### Human Approval/Rejection Decisions Only
```
log_type: "policy_decision" AND decision_type: "human_approval"
```

### Tool Call Decisions Only
```
log_type: "policy_decision" AND decision_type: "tool_call"
```

### Guardrails Decisions
```
log_type: "policy_decision" AND (decision_type: "guardrails_input" OR decision_type: "guardrails_output")
```

## Filter by Result

### Rejected/Denied Decisions
```
log_type: "policy_decision" AND result: "deny"
```

### Approved/Allowed Decisions
```
log_type: "policy_decision" AND result: "allow"
```

### Decisions Requiring Approval
```
log_type: "policy_decision" AND result: "require_approval"
```

## Filter by Agent

### Human Review Decisions
```
log_type: "policy_decision" AND agent_id: "HumanReviewer"
```

### Planner Agent Decisions
```
log_type: "policy_decision" AND agent_id: "PlannerAgent"
```

### Executor Agent Decisions
```
log_type: "policy_decision" AND agent_id: "ExecutorAgent"
```

## Filter by Task ID

If you want to see all decisions for a specific task:
```
log_type: "policy_decision" AND context_task_id: "task_20251222_123456_789012"
```

## Useful Field Combinations

### See Human Rejections
```
log_type: "policy_decision" AND decision_type: "human_approval" AND result: "deny"
```

### See Tool Calls That Were Denied
```
log_type: "policy_decision" AND decision_type: "tool_call" AND result: "deny"
```

### See Recent Human Decisions
```
log_type: "policy_decision" AND decision_type: "human_approval"
```
Then sort by `@timestamp` descending.

## Saved Searches

You can save these filters in Kibana:
1. Apply the filter
2. Click "Save" in the top menu
3. Give it a name like "Human Approval Decisions"
4. Access it later from "Saved Objects" → "Searches"
