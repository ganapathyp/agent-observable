# How to Run TaskPilot and Verify Jaeger Hierarchy

## Prerequisites

1. **Docker services running** (Jaeger, Prometheus, Grafana, Elasticsearch, Kibana, OTEL Collector)
2. **Python virtual environment** activated
3. **Environment variables** configured (`.env` file)

---

## Step 1: Start Docker Services

```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/agent-observable/examples/taskpilot

# Start all observability services
docker-compose -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose -f docker-compose.observability.yml ps
```

**Expected**: All 7 services should show as "Up" or "running"

---

## Step 2: Activate Virtual Environment

```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/agent-observable/examples/taskpilot

# Activate virtual environment
source .venv/bin/activate

# Verify Python path
which python3
```

---

## Step 3: Verify Environment Configuration

```bash
# Check .env file exists
ls -la .env

# Verify key variables (if needed)
cat .env | grep -E "OPENAI_API_KEY|AZURE_OPENAI"
```

**Note**: Make sure `OPENAI_API_KEY` or Azure OpenAI credentials are set.

---

## Step 4: Run TaskPilot (Script Mode)

### Option A: Run Once and Exit

```bash
python3 main.py
```

This will:
- Run a single workflow execution
- Create traces in Jaeger
- Exit after completion

### Option B: Run in Server Mode (Metrics Only)

```bash
python3 main.py --server --port 8000
```

This will:
- Start FastAPI server on port 8000
- **Expose metrics endpoints only** (no workflow execution)
- Keep running until interrupted (Ctrl+C)
- **Run workflows separately** in another terminal: `python3 main.py "task description"`

**Endpoints**:
- http://localhost:8000/ - Root endpoint
- http://localhost:8000/metrics - Prometheus metrics
- http://localhost:8000/health - Health check
- http://localhost:8000/golden-signals - Golden signals

**Note**: Server mode is decoupled from workflow execution. Keep the server running for Prometheus scraping, and run workflows separately as needed.

---

## Step 5: Verify Jaeger Hierarchy

### Option A: Using Jaeger UI (Recommended)

1. **Open Jaeger UI**:
   ```
   http://localhost:16686
   ```

2. **Select Service**:
   - Service: `taskpilot`
   - Click "Find Traces"

3. **Verify Hierarchy**:
   - Click on a trace
   - You should see:
     ```
     taskpilot.workflow.run (root span)
       ├─ taskpilot.agent.PlannerAgent.run (child)
       ├─ taskpilot.agent.ReviewerAgent.run (child)
       └─ taskpilot.agent.ExecutorAgent.run (child)
     ```

### Option B: Using Jaeger API

```bash
# Get latest trace
curl -s 'http://localhost:16686/api/traces?service=taskpilot&limit=1' | \
  python3 -m json.tool | \
  grep -A 5 '"operationName"'

# Check for child spans
curl -s 'http://localhost:16686/api/traces?service=taskpilot&limit=1' | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('data'):
    trace = data['data'][0]
    print(f'Total spans: {len(trace[\"spans\"])}')
    print(f'Has children: {any(s.get(\"references\") for s in trace[\"spans\"])}')
    for span in trace['spans']:
        refs = span.get('references', [])
        if refs:
            print(f'  {span[\"operationName\"]} has {len(refs)} reference(s)')
"
```

**Expected Output**:
```
Total spans: 4+ (workflow + 3 agents)
Has children: True
  taskpilot.agent.PlannerAgent.run has 1 reference(s)
  taskpilot.agent.ReviewerAgent.run has 1 reference(s)
  taskpilot.agent.ExecutorAgent.run has 1 reference(s)
```

---

## Step 6: Verify Other Observability Features

### Policy Decisions

```bash
# Check decision logs
tail -5 decision_logs.jsonl | python3 -m json.tool

# Count decisions
wc -l decision_logs.jsonl
```

### Metrics (Prometheus)

```bash
# Query metrics
curl 'http://localhost:9090/api/v1/query?query=workflow_runs_total'
curl 'http://localhost:9090/api/v1/query?query=agent_invocations_total'
```

### Logs (Kibana)

1. Open Kibana: http://localhost:5601
2. Go to Discover
3. Search for `taskpilot` logs

---

## Troubleshooting

### Issue: No traces in Jaeger

**Check**:
1. OTEL Collector is running: `docker ps | grep otel`
2. OTEL endpoint is correct: `http://localhost:4317`
3. Check logs: `docker-compose -f docker-compose.observability.yml logs otel-collector`

### Issue: Only workflow span, no agent spans

**Check**:
1. Verify global tracer is set: Check `setup_observability()` was called
2. Check middleware is attached to agents
3. Verify request_id matches across spans

### Issue: Services not starting

```bash
# Check Docker logs
docker-compose -f docker-compose.observability.yml logs

# Restart services
docker-compose -f docker-compose.observability.yml restart

# Rebuild if needed
docker-compose -f docker-compose.observability.yml up -d --build
```

---

## Quick Test Script

```bash
#!/bin/bash
# Quick verification script

echo "1. Checking Docker services..."
docker-compose -f docker-compose.observability.yml ps | grep -E "Up|running" | wc -l

echo "2. Running workflow..."
python3 main.py

echo "3. Checking Jaeger traces..."
sleep 2
curl -s 'http://localhost:16686/api/traces?service=taskpilot&limit=1' | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('data'):
    trace = data['data'][0]
    print(f'✅ Found trace with {len(trace[\"spans\"])} spans')
    print(f'✅ Has children: {any(s.get(\"references\") for s in trace[\"spans\"])}')
else:
    print('❌ No traces found')
"
```

---

## Expected Results

✅ **Jaeger**: Shows workflow → agents hierarchy  
✅ **Policy Decisions**: Logged in `decision_logs.jsonl`  
✅ **Metrics**: Available in Prometheus  
✅ **Logs**: Available in Kibana  
✅ **Traces**: Proper parent-child relationships  

---

## Next Steps

1. Run workflow: `python3 main.py`
2. Check Jaeger: http://localhost:16686
3. Verify hierarchy shows workflow as parent with agent children
4. Check policy decisions: `tail decision_logs.jsonl`
5. View metrics: http://localhost:9090

**Status**: ✅ System ready to run!
