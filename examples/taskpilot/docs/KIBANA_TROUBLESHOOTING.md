# Kibana Troubleshooting Guide

**Issue:** Not seeing data in Kibana Discover view

**Status:** ✅ Data is in Elasticsearch (60,764+ documents in today's index)

---

## Quick Fix Steps

### Step 1: Select the Correct Index Pattern

1. Go to **Kibana**: http://localhost:5601
2. Click **Discover** (compass icon in left sidebar)
3. If you see "No data" or empty results:
   - Click the **index pattern dropdown** (top left, shows current pattern)
   - Select: **`taskpilot-logs-*`** or **`.ds-taskpilot-logs-*`**
   - If neither appears, go to **Stack Management → Index Patterns** and create one

### Step 2: Set Time Range

**Critical:** Kibana only shows data within the selected time range!

1. Click the **time picker** (top right, shows "Last 15 minutes" by default)
2. Select: **"Last 24 hours"** or **"Last 7 days"**
3. Click **Update**

**Why:** Your demo data has timestamps from today, but Kibana defaults to "Last 15 minutes" which might not include your data.

### Step 3: Verify Data is Visible

After setting time range, you should see:
- **Document count** in top right (should show 60,000+)
- **Log entries** in the main view
- **Fields** in the left sidebar

---

## Verify Data Exists

### Check Elasticsearch Directly

```bash
# Count documents
curl 'http://localhost:9200/.ds-taskpilot-logs-2025.12.24-*/_count'

# Search for scenario
curl 'http://localhost:9200/.ds-taskpilot-logs-*/_search?q=scenario:cost_optimization&size=1'
```

**Expected:** Should return document counts and sample documents.

### Check Filebeat

```bash
# Check Filebeat logs
docker logs taskpilot-filebeat --tail 50 | grep -i "taskpilot\|error"
```

**Expected:** Should show Filebeat reading `/var/log/taskpilot/taskpilot.log`

---

## Common Issues & Solutions

### Issue 1: "No data" in Discover

**Cause:** Time range too narrow or index pattern not selected

**Solution:**
1. Set time range to **"Last 24 hours"** or **"Last 7 days"**
2. Verify index pattern is selected (should show `taskpilot-logs-*` or `.ds-taskpilot-logs-*`)
3. Click **Refresh** button

### Issue 2: Index Pattern Not Found

**Cause:** Index pattern not created

**Solution:**
1. Go to **Stack Management → Index Patterns**
2. Click **Create index pattern**
3. Pattern: `taskpilot-logs-*` or `.ds-taskpilot-logs-*`
4. Time field: `@timestamp`
5. Click **Create index pattern**

**Or run the setup script:**
```bash
python scripts/setup_kibana_index.py
```

### Issue 3: Filters Don't Work

**Cause:** Field names might be different or need to be refreshed

**Solution:**
1. Check field names in left sidebar
2. Use exact field names:
   - `scenario` (not `scenario.keyword`)
   - `level` (not `level.keyword`)
   - `log_type` (not `log_type.keyword`)
3. If field doesn't appear, click **Refresh** in Discover

### Issue 4: Old Data Only

**Cause:** Filebeat stopped shipping new logs

**Solution:**
1. Check if log file exists and has new data:
   ```bash
   ls -lh logs/taskpilot.log
   wc -l logs/taskpilot.log
   ```
2. Trigger Filebeat to re-read:
   ```bash
   touch logs/taskpilot.log
   ```
3. Wait 30 seconds for Filebeat to ship
4. Refresh Kibana Discover view

---

## Filter Examples

### By Scenario

```
scenario:cost_optimization
scenario:performance_bottleneck
scenario:policy_violations
scenario:error_patterns
```

### By Log Level

```
level:ERROR
level:INFO
level:WARNING
```

### By Log Type

```
log_type:policy_decision
```

### Combined Filters

```
scenario:cost_optimization AND level:INFO
level:ERROR AND error_code:TOOL_TIMEOUT
log_type:policy_decision AND result:deny
```

---

## Verify Setup

### 1. Check Index Pattern

1. Go to **Stack Management → Index Patterns**
2. Find `taskpilot-logs-*` or `.ds-taskpilot-logs-*`
3. Click on it
4. Verify:
   - **Time field:** `@timestamp`
   - **Indices matched:** Should show 4+ indices
   - **Field count:** Should show 50+ fields

### 2. Check Time Range

1. In **Discover**, check time picker (top right)
2. Should be set to **"Last 24 hours"** or wider
3. Click **Update** if changed

### 3. Check Field Availability

1. In **Discover**, look at left sidebar
2. Should see fields like:
   - `@timestamp`
   - `scenario`
   - `level`
   - `message`
   - `request_id`
   - `agent_name`
   - `log_type`

If fields don't appear:
1. Click **Refresh** button
2. Or go to index pattern settings and click **Refresh field list**

---

## Quick Test Query

Try this in Kibana Discover:

1. **Time range:** Last 24 hours
2. **Filter:** `scenario:cost_optimization`
3. **Expected:** Should see 110+ documents

If you see 0 results:
- Check time range (expand to "Last 7 days")
- Check filter syntax (no quotes needed)
- Verify field exists in left sidebar

---

## Manual Data Verification

### Check Elasticsearch

```bash
# Total documents today
curl 'http://localhost:9200/.ds-taskpilot-logs-2025.12.24-*/_count'

# Documents with scenario
curl 'http://localhost:9200/.ds-taskpilot-logs-*/_search?q=scenario:cost_optimization&size=1&pretty'
```

### Check Log File

```bash
# Count lines
wc -l logs/taskpilot.log

# Check last entry
tail -1 logs/taskpilot.log | python3 -m json.tool

# Check for scenario field
grep -c "cost_optimization" logs/taskpilot.log
```

---

## Still Not Working?

1. **Restart Filebeat:**
   ```bash
   docker restart taskpilot-filebeat
   ```

2. **Check Filebeat logs:**
   ```bash
   docker logs taskpilot-filebeat --tail 100
   ```

3. **Regenerate data:**
   ```bash
   python scripts/generate_demo_data.py
   touch logs/taskpilot.log  # Trigger Filebeat
   ```

4. **Wait 60 seconds** for Filebeat to ship logs

5. **Refresh Kibana** Discover view

---

## Expected Results

After following these steps, you should see:

- ✅ **60,000+ documents** in Discover (document count in top right)
- ✅ **Log entries** visible in main view
- ✅ **Fields** listed in left sidebar
- ✅ **Filters work** (scenario:cost_optimization shows 110+ docs)
- ✅ **Time range** shows data from last 24 hours

If you still don't see data, check:
1. Time range is set correctly
2. Index pattern is selected
3. Elasticsearch has data (verify with curl commands above)
4. Filebeat is running and shipping logs
