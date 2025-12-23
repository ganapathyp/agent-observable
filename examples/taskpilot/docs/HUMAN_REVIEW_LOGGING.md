# Human Review Decision Logging

## Overview

When you approve or reject tasks using the review scripts, these actions are now logged as policy decisions for audit and compliance.

## What Gets Logged

When you use `review_tasks.py` to approve or reject a task:

- **Decision Type**: `human_approval`
- **Result**: `allow` (for approve) or `deny` (for reject)
- **Tool**: `review_task`
- **Agent**: `HumanReviewer`
- **Context**: Includes task_id, task_title, task_priority, reviewer_response, and human_decision

## Viewing in Kibana

1. Open Kibana: http://localhost:5601
2. Go to Discover
3. Select index pattern: `taskpilot-logs-*`
4. Set time range to "Last 24 hours" (or longer)
5. Filter by: `log_type: "policy_decision" AND decision_type: "human_approval"`

Or use this direct link:
```
http://localhost:5601/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:now-24h,to:now))&_a=(columns:!(),filters:!(),index:taskpilot_logs_star,interval:auto,query:(language:kuery,query:'log_type:%22policy_decision%22%20AND%20decision_type:%22human_approval%22'),sort:!(!('@timestamp',desc)))
```

## Viewing via CLI

```bash
# View recent human review decisions
python3 scripts/utils/view_decision_logs.py --recent 10

# View only rejected tasks
python3 scripts/utils/view_decision_logs.py --recent 20 | grep "deny"

# View summary
python3 scripts/utils/view_decision_logs.py --summary
```

## Important Notes

- **Time Range**: Make sure your Kibana time range includes when you made the decision (extend to "Last 24 hours" if needed)
- **Index Pattern**: Use `taskpilot-logs-*` (not `taskpilot*`)
- **Delay**: Decisions are batched and flushed every 5 seconds, so wait a few seconds after rejecting/approving before checking Kibana
