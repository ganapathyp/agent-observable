# Fix: Only Seeing 11 Policy Decisions Instead of 264

## Problem

You're filtering by `log_type: "policy_decision"` but only seeing **11 hits** instead of all **264 policy decisions**.

## Root Cause

Your **time range is too narrow**. You're currently viewing:
- **Time Range**: Dec 22, 2025 @ 13:37:59 - 13:44 (only 6 minutes!)
- **Hits**: 11 records

But policy decisions span a much wider time range.

## Solution: Expand Time Range

### Quick Fix in Kibana:

1. **Click the time picker** (top-right corner of Kibana)
2. **Select a wider range**:
   - **"Last 24 hours"** (recommended for recent data)
   - **"Last 7 days"** (to see all historical data)
   - Or manually set: **"Dec 22, 2025 00:00" to "Dec 22, 2025 23:59"**

3. **Click "Update"**

### Expected Results After Expanding:

- **Total hits**: Should show **264 records** (or close to it)
- **decision_type breakdown**: Should show:
  - `tool_call`: 263 records
  - `human_approval`: 1+ records

## Verify It's Working

After expanding the time range:

1. **Check total hits**: Should be ~264 (not 11)
2. **Click on `decision_type` field** in left sidebar
3. **You should see**:
   - `tool_call` with count ~263
   - `human_approval` with count 1+

## Why This Happens

Kibana only shows documents **within your selected time range**. If your time range is:
- **Too narrow** (6 minutes) → Only shows 11 records from that window
- **Correct range** (24 hours) → Shows all 264 records

## Single Filter Still Works

✅ **Your filter is correct**: `log_type: "policy_decision"`  
✅ **No need to add `decision_type` filter**  
✅ **Just expand the time range** to see all decision types

## Direct Link with Correct Time Range

Use this link to open Kibana with the correct time range:

```
http://localhost:5601/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:now-24h,to:now))&_a=(columns:!(),filters:!((query:(match_phrase:(log_type:'policy_decision')))),index:taskpilot_logs_star,interval:auto,query:(language:kuery,query:''),sort:!(!('@timestamp',desc)))
```

This link:
- ✅ Sets time range to "Last 24 hours"
- ✅ Filters by `log_type: "policy_decision"`
- ✅ Shows all decision types (tool_call + human_approval)
