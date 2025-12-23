# Kibana Quick Filter Guide

## Single Filter for All Policy Decisions

**Use this ONE filter to see ALL policy decisions (tool calls, human approvals, guardrails, etc.):**

```
log_type: "policy_decision"
```

This filter will show:
- ✅ All `tool_call` decisions
- ✅ All `human_approval` decisions  
- ✅ All `guardrails_input` decisions
- ✅ All `guardrails_output` decisions
- ✅ All `ingress` decisions

## How to Verify in Kibana

1. **Open Kibana Discover**: http://localhost:5601/app/discover
2. **Select index pattern**: `taskpilot-logs-*`
3. **Add filter**: In the search bar, type: `log_type: "policy_decision"`
4. **Check the breakdown**: Click on the `decision_type` field in the left sidebar
   - You should see multiple decision types listed
   - Each type shows its document count

## Expected Results

When filtering by `log_type: "policy_decision"`, you should see:
- **decision_type** field showing values like:
  - `tool_call` (most common)
  - `human_approval` (your review decisions)
  - `guardrails_input` (if any)
  - `guardrails_output` (if any)

## If You Only See One Type

If you're only seeing one decision type when filtering by `log_type: "policy_decision"`:

1. **Check your time range**: Make sure it covers when decisions were made
   - Try "Last 24 hours" or "Last 7 days"

2. **Check the field breakdown**: 
   - Click on `decision_type` in the left sidebar
   - This shows all decision types present in your filtered results

3. **Verify the filter**: 
   - Make sure the filter is `log_type: "policy_decision"` (with quotes)
   - Not `log_type: policy_decision` (without quotes)

4. **Clear other filters**: 
   - Remove any other filters that might be limiting results
   - Check the "Active filters" section

## Quick Test

To verify both types are present:
1. Filter: `log_type: "policy_decision"`
2. Look at the `decision_type` field breakdown
3. You should see at least:
   - `tool_call` (263+ records)
   - `human_approval` (1+ records)

## Summary

✅ **One filter works for all**: `log_type: "policy_decision"` shows ALL decision types
✅ **No need for multiple filters**: You don't need to add `decision_type` filter
✅ **Use `decision_type` only if**: You want to see a specific type (e.g., only human approvals)
