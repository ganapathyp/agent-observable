#!/bin/bash
# Verify observability stack integration

echo "🔍 Observability Integration Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Metrics
echo "1️⃣  METRICS"
echo "----------"
METRICS=$(curl -s http://localhost:8001/metrics 2>/dev/null | head -3)
if [ -n "$METRICS" ]; then
    echo -e "${GREEN}✅ Metrics endpoint working${NC}"
    echo "   Sample:"
    echo "$METRICS" | head -3 | sed 's/^/   /'
else
    echo -e "${RED}❌ Metrics endpoint not responding${NC}"
    echo "   Start: python3 metrics_server.py"
fi

# Check Prometheus
PROM_STATUS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); targets=[t for t in data.get('data', {}).get('activeTargets', []) if t['labels']['job']=='taskpilot']; print(targets[0]['health'] if targets else 'NOT_FOUND')" 2>/dev/null)
if [ "$PROM_STATUS" = "up" ]; then
    echo -e "${GREEN}✅ Prometheus target: UP${NC}"
elif [ "$PROM_STATUS" = "down" ]; then
    echo -e "${RED}❌ Prometheus target: DOWN${NC}"
    echo "   Check: http://localhost:9090/targets"
else
    echo -e "${YELLOW}⚠️  Prometheus target: $PROM_STATUS${NC}"
fi
echo ""

# 2. Traces
echo "2️⃣  TRACES"
echo "----------"
if [ -f "traces.jsonl" ]; then
    TRACE_COUNT=$(wc -l < traces.jsonl 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ traces.jsonl exists${NC} ($TRACE_COUNT spans)"
    echo "   View: python view_traces.py --agents"
else
    echo -e "${YELLOW}⚠️  No traces.jsonl (run main.py first)${NC}"
fi

# Check OpenTelemetry collector
OTEL_STATUS=$(docker ps --format "{{.Status}}" --filter "name=taskpilot-otel-collector" 2>/dev/null | grep -q "Up" && echo "running" || echo "not_running")
if [ "$OTEL_STATUS" = "running" ]; then
    echo -e "${GREEN}✅ OpenTelemetry collector: Running${NC}"
    echo "   Note: Application not integrated yet (traces only in file)"
else
    echo -e "${RED}❌ OpenTelemetry collector: Not running${NC}"
fi

# Check Jaeger
if curl -s http://localhost:16686 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Jaeger UI: Accessible${NC}"
    echo "   URL: http://localhost:16686"
else
    echo -e "${RED}❌ Jaeger UI: Not accessible${NC}"
fi
echo ""

# 3. Logs
echo "3️⃣  LOGS"
echo "--------"
LOG_FILES=$(ls logs/*.log 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOG_FILES" -gt 0 ]; then
    echo -e "${GREEN}✅ Log files found: $LOG_FILES${NC}"
    ls -lh logs/*.log 2>/dev/null | head -3 | awk '{print "   " $9 " (" $5 ")"}'
else
    echo -e "${YELLOW}⚠️  No log files in logs/ directory${NC}"
    echo "   Application not writing JSON logs yet"
fi

# Check Filebeat
FILEBEAT_STATUS=$(docker ps --format "{{.Status}}" --filter "name=taskpilot-filebeat" 2>/dev/null | grep -q "Up" && echo "running" || echo "not_running")
if [ "$FILEBEAT_STATUS" = "running" ]; then
    echo -e "${GREEN}✅ Filebeat: Running${NC}"
else
    echo -e "${RED}❌ Filebeat: Not running${NC}"
fi

# Check Elasticsearch
if curl -s http://localhost:9200 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Elasticsearch: Accessible${NC}"
else
    echo -e "${RED}❌ Elasticsearch: Not accessible${NC}"
fi

# Check Kibana
if curl -s http://localhost:5601/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kibana: Accessible${NC}"
    echo "   URL: http://localhost:5601"
    echo "   Note: Need to create index pattern: taskpilot-logs-*"
else
    echo -e "${RED}❌ Kibana: Not accessible${NC}"
fi
echo ""

# Summary
echo "📊 SUMMARY"
echo "----------"
echo "Metrics:  $(if [ -n "$METRICS" ] && [ "$PROM_STATUS" = "up" ]; then echo "✅ Working"; elif [ -n "$METRICS" ]; then echo "⚠️  Endpoint OK, Prometheus DOWN"; else echo "❌ Not working"; fi)"
echo "Traces:   $(if [ -f "traces.jsonl" ]; then echo "✅ File exists (not in Jaeger)"; else echo "⚠️  No traces"; fi)"
echo "Logs:     $(if [ "$LOG_FILES" -gt 0 ]; then echo "✅ Files exist"; else echo "⚠️  No log files"; fi)"
echo ""
echo "Next steps:"
echo "  1. Metrics: Check Grafana → http://localhost:3000"
echo "  2. Traces:  python view_traces.py --agents"
echo "  3. Logs:   Need to add JSON logging to application"
