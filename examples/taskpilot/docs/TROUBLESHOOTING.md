# Troubleshooting Guide

## Common Issues and Solutions

### Metrics Not Showing

#### Problem: No metrics in Prometheus/Grafana

**Checklist:**
1. ✅ Is `main.py --server` running? `curl http://localhost:8000/health`
2. ✅ Have workflows been executed? `python main.py` (at least once)
3. ✅ Is Prometheus scraping? http://localhost:9090/targets (should show "UP")
4. ✅ Wait 15 seconds after running workflows (Prometheus scrape interval)

**Solutions:**
```bash
# 1. Start server
python main.py --server --port 8000

# 2. Run workflow to generate metrics
python main.py

# 3. Wait 15 seconds, then check Prometheus
open http://localhost:9090
# Query: workflow_runs
```

**If Prometheus target is DOWN:**
- Check if port 8000 is accessible: `curl http://localhost:8000/metrics`
- Verify Prometheus config: `observability/prometheus/prometheus.yml`
- Restart Prometheus: `docker-compose -f docker-compose.observability.yml restart prometheus`

---

### Traces Not Showing in Jaeger

#### Problem: No traces in Jaeger UI

**Checklist:**
1. ✅ Is OpenTelemetry enabled? Check `OTEL_ENABLED` env var (default: true)
2. ✅ Is OTel Collector running? `docker ps | grep otel-collector`
3. ✅ Are workflows being executed? Traces created automatically
4. ✅ Check file traces: `python scripts/utils/view_traces.py --agents`

**Solutions:**
```bash
# 1. Verify OTel Collector is running
docker ps | grep taskpilot-otel-collector

# 2. Check OTel config
cat observability/otel/collector-config.yml

# 3. Restart OTel Collector
docker-compose -f docker-compose.observability.yml restart otel-collector

# 4. Run workflow and check Jaeger
python main.py
# Wait a few seconds, then check Jaeger: http://localhost:16686
```

**If traces still not showing:**
- Check application logs for OTel errors
- Verify OTLP endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
- Check OTel Collector logs: `docker logs taskpilot-otel-collector`

---

### Logs Not Showing in Kibana

#### Problem: No logs in Kibana

**Checklist:**
1. ✅ Is Filebeat running? `docker ps | grep filebeat`
2. ✅ Are logs being written? `ls -la logs/taskpilot.log`
3. ✅ Is Elasticsearch running? `curl http://localhost:9200`
4. ✅ Is index pattern created? Kibana → Management → Index Patterns

**Solutions:**
```bash
# 1. Check if logs are being written
tail -f logs/taskpilot.log

# 2. Verify Filebeat is running
docker ps | grep taskpilot-filebeat

# 3. Check Filebeat logs
docker logs taskpilot-filebeat

# 4. Create index pattern in Kibana
# Open: http://localhost:5601
# Go to: Management → Index Patterns → Create
# Pattern: taskpilot-logs-*
```

**If logs still not showing:**
- Check file permissions: `ls -la logs/taskpilot.log`
- Verify Filebeat config: `observability/filebeat/filebeat.yml`
- Check Elasticsearch: `curl http://localhost:9200/_cat/indices`

---

### 404 Error on /metrics Endpoint

#### Problem: `404 File not found` when accessing `/metrics`

**Cause:** Server not running or wrong port

**Solution:**
```bash
# Check if server is running
curl http://localhost:8000/health

# If not running, start it
python main.py --server --port 8000

# Then test
curl http://localhost:8000/metrics
```

**If port 8000 is in use:**
```bash
# Check what's using it
lsof -ti:8000

# Kill it
kill $(lsof -ti:8000)

# Or use different port
python main.py --server --port 8002
# Update Prometheus config to use port 8002
```

---

### Cost Metrics Not Appearing

#### Problem: No cost metrics (`llm_cost_total`)

**Cause:** Token usage not available in LLM responses

**Check:**
```bash
# Check if cost metrics exist
curl http://localhost:8000/metrics | grep cost

# If empty, token usage may not be in response format
# Check middleware logs for "Token usage not available"
```

**Solution:**
- Cost tracking requires token usage in LLM response
- Check if LLM provider returns token usage
- Verify `track_llm_metrics()` is being called in middleware

---

### Prometheus Target Shows DOWN

#### Problem: Prometheus target status is "DOWN"

**Check error message:**
- Open: http://localhost:9090/targets
- Click on target to see error

**Common errors:**

**"connection refused"**
- Metrics server not running
- Wrong port in Prometheus config

**Fix:**
```bash
# Start server
python main.py --server --port 8000

# Verify endpoint
curl http://localhost:8000/metrics

# Update Prometheus config if needed
# observability/prometheus/prometheus.yml
```

**"no such host"**
- `host.docker.internal` not accessible from Docker

**Fix:**
```bash
# Restart Prometheus
docker-compose -f docker-compose.observability.yml restart prometheus

# Or use IP address instead of host.docker.internal
```

---

### Grafana Shows No Data

#### Problem: Grafana dashboards are empty

**Checklist:**
1. ✅ Is Prometheus running? `curl http://localhost:9090/-/healthy`
2. ✅ Does Prometheus have data? Query `workflow_runs` in Prometheus UI
3. ✅ Is Grafana connected to Prometheus? Check data source
4. ✅ Have workflows been executed? Metrics won't appear until workflows run

**Solutions:**
```bash
# 1. Verify Prometheus has data
open http://localhost:9090
# Query: workflow_runs
# Should show a number if metrics exist

# 2. Check Grafana data source
# Open: http://localhost:3000
# Go to: Configuration → Data Sources → Prometheus
# Should show: http://prometheus:9090

# 3. Run workflow to generate metrics
python main.py

# 4. Wait 15 seconds, refresh Grafana
```

---

### Services Not Starting

#### Problem: Docker services fail to start

**Check logs:**
```bash
# Check specific service
docker logs taskpilot-prometheus
docker logs taskpilot-grafana

# Check all services
docker-compose -f docker-compose.observability.yml logs
```

**Common issues:**

**Port already in use:**
```bash
# Find what's using the port
lsof -ti:9090  # Prometheus
lsof -ti:3000  # Grafana

# Kill it or change port in docker-compose.yml
```

**Volume mount issues:**
```bash
# Create required directories
# Configs are in the project's observability/ folder - no setup needed!
# All configs are version-controlled in the repository

# Check that config files exist in project
ls -la observability/prometheus/prometheus.yml
ls -la observability/filebeat/filebeat.yml
ls -la logs/
```

**Insufficient resources:**
```bash
# Check Docker resources
docker stats

# Stop other containers if needed
docker ps
docker stop <container-id>
```

---

### Tests Hanging

#### Problem: Tests hang and don't complete

**Cause:** File I/O locking in MetricsCollector

**Solution:**
- Tests use in-memory metrics (`metrics_file=None`)
- Fixture in `conftest.py` resets global singleton
- All new tests use `MetricsCollector(metrics_file=None)`

**If tests still hang:**
```bash
# Run with timeout
pytest tests/ --timeout=10

# Or run specific test
pytest tests/test_golden_signals.py::TestGoldenSignals::test_golden_signals_empty_metrics -v
```

---

## Quick Diagnostic Commands

### Check All Services

```bash
# Check Docker services
docker ps | grep taskpilot

# Check application server
curl http://localhost:8000/health

# Check metrics endpoint
curl http://localhost:8000/metrics | head -10

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

### Verify Data Flow

```bash
# 1. Run workflow
python main.py

# 2. Check metrics file
cat metrics.json | jq '.counters'

# 3. Check traces file
tail -5 traces.jsonl | jq

# 4. Check logs file
tail -5 logs/taskpilot.log | jq

# 5. Check Prometheus (wait 15 seconds)
curl 'http://localhost:9090/api/v1/query?query=workflow_runs' | jq
```

---

## Getting Help

### Check Documentation

- **Observability Integration:** [details/OBSERVABILITY_INTEGRATION.md](details/OBSERVABILITY_INTEGRATION.md)
- **Docker Setup:** [details/DOCKER_SETUP.md](details/DOCKER_SETUP.md)
- **Architecture:** [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)

### Check Logs

```bash
# Application logs
tail -f logs/taskpilot.log

# Docker service logs
docker logs taskpilot-prometheus
docker logs taskpilot-grafana
docker logs taskpilot-otel-collector
```

---

## Additional Troubleshooting

### Docker Mount Issues (macOS)

**Problem:** Docker Desktop on macOS requires explicit file sharing configuration.

**Solution:**
1. Open Docker Desktop → Settings → Resources → File Sharing
2. Add parent directory: `/Users/your-username/dev` (or project parent)
3. Click "Apply & Restart"
4. Wait for Docker to restart

**Alternative:** Use absolute paths in `docker-compose.yml` or copy configs into containers.

### Kibana Not Showing Logs

**Problem:** Logs written but not visible in Kibana.

**Checklist:**
1. ✅ Is Filebeat running? `docker ps | grep filebeat`
2. ✅ Are logs being written? `tail -f logs/taskpilot.log`
3. ✅ Is Elasticsearch running? `curl http://localhost:9200`
4. ✅ Is index pattern created? Kibana → Management → Index Patterns

**Solution:**
```bash
# 1. Check if logs are being written
tail -f logs/taskpilot.log

# 2. Verify Filebeat is running
docker ps | grep taskpilot-filebeat

# 3. Check Filebeat logs
docker logs taskpilot-filebeat

# 4. Create index pattern in Kibana
# Open: http://localhost:5601
# Go to: Management → Index Patterns → Create
# Pattern: taskpilot-logs-*
```

**If logs still not showing:**
- Check file permissions: `ls -la logs/taskpilot.log`
- Verify Filebeat config: `observability/filebeat/filebeat.yml`
- Check Elasticsearch: `curl http://localhost:9200/_cat/indices`

### Metrics File Not Found (404)

**Problem:** `404 File not found` when accessing `/metrics`

**Cause:** Server not running or wrong port

**Solution:**
```bash
# Check if server is running
curl http://localhost:8000/health

# If not running, start it
python main.py --server --port 8000

# Then test
curl http://localhost:8000/metrics
```

**If port 8000 is in use:**
```bash
# Check what's using it
lsof -ti:8000

# Kill it
kill $(lsof -ti:8000)

# Or use different port
python main.py --server --port 8002
# Update Prometheus config to use port 8002
```

### Metrics Not Persisting

**Problem:** Metrics reset after restart

**Check:**
- Is `metrics.json` being written? `ls -la metrics.json`
- Check file permissions: `ls -la metrics.json`
- Verify metrics file path in config: Check `METRICS_FILE` env var

**Solution:**
```bash
# Check if metrics file exists and is writable
ls -la metrics.json
cat metrics.json | jq

# If missing, run application to generate
python main.py

# Check metrics file again
cat metrics.json | jq
```

---

*For more details, see [details/OBSERVABILITY_INTEGRATION.md](details/OBSERVABILITY_INTEGRATION.md) and [CONFIGURATION.md](CONFIGURATION.md).*
