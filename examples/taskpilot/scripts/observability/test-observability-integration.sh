#!/bin/bash
# Test full observability integration

echo "🧪 Testing Full Observability Integration"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_check() {
    local name=$1
    local command=$2
    
    echo -n "Testing $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

# 1. Application runs
echo "1️⃣  Application Test"
test_check "Application runs" "source .venv/bin/activate 2>/dev/null && timeout 30 python main.py > /tmp/test_run.log 2>&1"
echo ""

# 2. Traces
echo "2️⃣  Traces"
test_check "traces.jsonl exists" "[ -f traces.jsonl ]"
test_check "Traces have content" "[ -s traces.jsonl ]"
test_check "view_traces.py works" "python view_traces.py --recent 1 > /dev/null 2>&1"
echo ""

# 3. Metrics
echo "3️⃣  Metrics"
test_check "metrics.json exists" "[ -f metrics.json ]"
test_check "Metrics endpoint responds" "curl -s http://localhost:8001/metrics | grep -q workflow_runs"
test_check "Prometheus target UP" "curl -s http://localhost:9090/api/v1/targets | python3 -c \"import sys, json; data=json.load(sys.stdin); targets=[t for t in data.get('data', {}).get('activeTargets', []) if t['labels']['job']=='taskpilot']; exit(0 if targets and targets[0]['health']=='up' else 1)\" 2>/dev/null"
echo ""

# 4. Logs
echo "4️⃣  Logs"
test_check "logs/taskpilot.log exists" "[ -f logs/taskpilot.log ]"
test_check "Log file has content" "[ -s logs/taskpilot.log ]"
test_check "Log file is JSON format" "head -1 logs/taskpilot.log | python3 -m json.tool > /dev/null 2>&1"
echo ""

# 5. OpenTelemetry/Jaeger
echo "5️⃣  OpenTelemetry/Jaeger"
test_check "Jaeger UI accessible" "curl -s http://localhost:16686 > /dev/null"
test_check "OpenTelemetry collector running" "docker ps | grep -q otel-collector"
echo ""

# 6. Elasticsearch/Kibana
echo "6️⃣  Elasticsearch/Kibana"
test_check "Elasticsearch accessible" "curl -s http://localhost:9200 > /dev/null"
test_check "Kibana accessible" "curl -s http://localhost:5601/api/status > /dev/null"
test_check "Filebeat running" "docker ps | grep -q filebeat"
echo ""

# Summary
echo "📊 Summary"
echo "----------"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  📊 View metrics: http://localhost:3000 (Grafana)"
    echo "  🔍 View traces: http://localhost:16686 (Jaeger)"
    echo "  📋 View logs: http://localhost:5601 (Kibana)"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed${NC}"
    echo ""
    echo "Check:"
    echo "  - Are all Docker services running? ./check-observability.sh"
    echo "  - Is metrics server running? python metrics_server.py"
    echo "  - Did you run main.py? python main.py"
    exit 1
fi
