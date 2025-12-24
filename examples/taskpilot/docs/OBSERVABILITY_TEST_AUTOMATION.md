# Observability Stack Test Automation

## Overview

Comprehensive automated testing for the entire observability stack:
- Docker services (start/fix)
- Data generation and verification
- Metrics, traces, logs
- Dashboards (auto-create if missing)
- Alerts (verify configuration)
- Leadership-ready metrics

## Quick Start

```bash
# Run comprehensive test
python3 scripts/test_observability_stack.py
```

## What It Tests

### 1. Docker Services ✅
- Checks Docker daemon
- Starts all observability services
- Verifies each service is running
- Tests HTTP endpoints

### 2. Data Generation 📊
- Checks TaskPilot server status
- Runs test workflow to generate data
- Waits for data propagation

### 3. Metrics 📈
- Verifies TaskPilot `/metrics` endpoint
- Checks Prometheus target status
- Queries key metrics in Prometheus
- Validates metric names and values

### 4. Traces 🔍
- Checks Jaeger service registration
- Verifies traces are being collected
- Validates trace hierarchy

### 5. Logs 📝
- Checks Elasticsearch indices
- Verifies Kibana accessibility
- Validates log file generation

### 6. Dashboards 📊
- Checks for Golden Signals dashboard
- **Auto-creates dashboard if missing**
- Verifies dashboard configuration

### 7. Alerts 🚨
- Verifies alert rules file exists
- Checks Prometheus alert configuration
- Validates alert system accessibility

### 8. Leadership Metrics 👔
- Tests Golden Signals API
- Verifies business metrics availability
- Ensures metrics are demo-ready

## Prerequisites

1. **Docker and Docker Compose** installed
2. **Python 3.8+** with required packages:
   ```bash
   pip install requests
   ```
3. **TaskPilot server** (optional, will be checked):
   ```bash
   python main.py --server --port 8000
   ```

## Usage

### Basic Test

```bash
cd /path/to/taskpilot
python3 scripts/test_observability_stack.py
```

### Expected Output

```
================================================================================
COMPREHENSIVE OBSERVABILITY STACK TEST
================================================================================

🔧 STEP 1: Docker Services
--------------------------------------------------------------------------------
  ✅ Docker Compose File
     Found: /path/to/docker-compose.observability.yml
  ✅ Docker Daemon
     Docker daemon is running
  ✅ Start Docker Services
     All services started successfully 🔧
  ✅ Prometheus Container
     Up 5 minutes
  ✅ Prometheus HTTP
     Endpoint accessible: http://localhost:9090/-/healthy
  ...

📊 STEP 2: Data Generation
--------------------------------------------------------------------------------
  ✅ TaskPilot Server
     Server is running
  ✅ Workflow Execution
     Test workflow executed successfully
  ...

📈 STEP 3: Metrics Verification
--------------------------------------------------------------------------------
  ✅ TaskPilot Metrics Endpoint
     Found 6/6 key metrics
  ✅ Prometheus Target
     Target health: up
  ✅ Prometheus Query: llm_cost_total
     Total LLM cost: 0.001234
  ...

================================================================================
TEST SUMMARY
================================================================================
Total Tests: 45
✅ Passed: 42
❌ Failed: 0
⚠️  Warnings: 3
🔧 Fixes Applied: 2
Pass Rate: 93.3%

📄 Report saved to: observability_test_report.json
```

## Test Report

The script generates a detailed JSON report:

```bash
cat observability_test_report.json
```

**Report includes:**
- Timestamp
- Summary statistics
- Detailed results for each test category
- Fixes applied
- Error messages and warnings

## Auto-Fixes

The script automatically applies fixes for:
- ✅ Starting Docker services
- ✅ Creating missing Grafana dashboards
- ✅ Generating test data

## Leadership Metrics Verification

The script specifically verifies metrics are **demo-ready**:

### Required Metrics
- `llm_cost_total` - Total LLM cost (USD)
- `workflow_success` - Successful workflows
- `policy_violations_total` - Policy violations
- `workflow_latency_ms_p95` - P95 latency

### Golden Signals API
- `success_rate` - Workflow success rate (%)
- `p95_latency` - P95 latency (ms)
- `cost_per_successful_task` - Cost per task (USD)
- `policy_violation_rate` - Policy violation rate (%)

## Troubleshooting

### Docker Services Won't Start

**Error**: `Mounts denied: The path ... is not shared`

**Fix**: Add project directory to Docker Desktop file sharing:
1. Docker Desktop → Settings → Resources → File Sharing
2. Add: `/Users/your-username/dev/code/maia v2/agent-observable`
3. Click "Apply & Restart"

See: `docs/DOCKER_FILE_SHARING_FIX.md`

### Prometheus Target Down

**Error**: `Target health: down`

**Fix**: 
1. Ensure TaskPilot server is running: `python main.py --server --port 8000`
2. Verify server binds to `0.0.0.0` (not `127.0.0.1`)
3. Check Prometheus can reach server: `docker exec taskpilot-prometheus wget -qO- http://host.docker.internal:8000/metrics`

See: `docs/PROMETHEUS_CONNECTION_FIX.md`

### No Metrics in Prometheus

**Error**: `No data (metric may be 0 or not scraped yet)`

**Fix**:
1. Run a workflow to generate metrics: `python main.py "Test task"`
2. Wait 15-30 seconds for Prometheus to scrape
3. Re-run test script

### Dashboard Creation Fails

**Error**: `Failed to create dashboard`

**Fix**:
1. Verify Grafana credentials (default: admin/admin)
2. Check dashboard JSON file exists: `observability/grafana/golden-signals-dashboard.json`
3. Manually import dashboard if needed

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Observability Stack Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install requests
      - name: Start Docker services
        run: |
          docker-compose -f docker-compose.observability.yml up -d
      - name: Run observability tests
        run: |
          python3 scripts/test_observability_stack.py
```

## Manual Verification

After running the test script, manually verify:

### 1. Prometheus
- Open: http://localhost:9090
- Check targets: Status → Targets
- Query metrics: Graph → `llm_cost_total`

### 2. Grafana
- Open: http://localhost:3000
- Login: admin/admin
- Check dashboard: Dashboards → Golden Signals

### 3. Jaeger
- Open: http://localhost:16686
- Search service: `taskpilot`
- Verify trace hierarchy

### 4. Kibana
- Open: http://localhost:5601
- Check indices: Management → Index Patterns
- Search logs: Discover

## Continuous Monitoring

Run the test script periodically to ensure observability stack remains healthy:

```bash
# Run every hour
*/60 * * * * cd /path/to/taskpilot && python3 scripts/test_observability_stack.py
```

## Related Documentation

- `docs/DOCKER_FILE_SHARING_FIX.md` - Docker file sharing issues
- `docs/PROMETHEUS_CONNECTION_FIX.md` - Prometheus connectivity
- `docs/METRICS_EXPORT_FIX.md` - Metrics export issues
- `docs/OBSERVABILITY_TOOLS_WALKTHROUGH.md` - Tool usage guide

## Support

If tests fail:
1. Review the test report: `observability_test_report.json`
2. Check service logs: `docker-compose -f docker-compose.observability.yml logs`
3. Verify configuration files
4. Check documentation for specific error messages
