#!/bin/bash
# End-to-end test for production-like observability stack

set -e

echo "🧪 End-to-End Observability Test"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_check() {
    local name=$1
    local command=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test function with output check
test_check_output() {
    local name=$1
    local command=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    output=$(eval "$command" 2>&1)
    if echo "$output" | grep -q "$expected"; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "  Expected: $expected"
        echo "  Got: $output"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "📋 Prerequisites Check"
echo "----------------------"

# Check Docker
test_check "Docker installed" "command -v docker"
test_check "Docker running" "docker ps > /dev/null"

# Check Python
test_check "Python 3.11+" "python3 --version | grep -E 'Python 3\.(1[1-9]|[2-9][0-9])'"

# Check dependencies
test_check "FastAPI installed" "python3 -c 'import fastapi' 2>/dev/null"
test_check "uvicorn installed" "python3 -c 'import uvicorn' 2>/dev/null"

echo ""
echo "🐳 Docker Services Check"
echo "----------------------"

# Check if services are running
test_check "Prometheus running" "docker ps | grep taskpilot-prometheus"
test_check "Grafana running" "docker ps | grep taskpilot-grafana"
test_check "Jaeger running" "docker ps | grep taskpilot-jaeger"
test_check "Elasticsearch running" "docker ps | grep taskpilot-elasticsearch"
test_check "Kibana running" "docker ps | grep taskpilot-kibana"
test_check "OpenTelemetry Collector running" "docker ps | grep taskpilot-otel-collector"

echo ""
echo "🌐 Service Endpoints Check"
echo "-------------------------"

# Check endpoints are accessible
test_check "Prometheus endpoint" "curl -s http://localhost:9090/-/healthy"
test_check "Grafana endpoint" "curl -s http://localhost:3000/api/health"
test_check "Jaeger endpoint" "curl -s http://localhost:16686"
test_check "Kibana endpoint" "curl -s http://localhost:5601/api/status"
test_check "Elasticsearch endpoint" "curl -s http://localhost:9200"

echo ""
echo "📊 Metrics Server Check"
echo "----------------------"

# Check if metrics server is running
METRICS_RUNNING=false
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    METRICS_RUNNING=true
    test_check "Metrics server running" "true"
    test_check "Metrics endpoint accessible" "curl -s http://localhost:8000/metrics | grep -q 'TYPE'"
    test_check "Health endpoint accessible" "curl -s http://localhost:8000/health | grep -q 'status'"
else
    echo -e "${YELLOW}⚠️  Metrics server not running${NC}"
    echo "   Start it with: python metrics_server.py"
    echo ""
fi

echo ""
echo "📈 Prometheus Integration Check"
echo "-------------------------------"

if [ "$METRICS_RUNNING" = true ]; then
    # Check if Prometheus can scrape metrics
    sleep 5  # Wait for Prometheus to scrape
    test_check_output "Prometheus scraping metrics" \
        "curl -s 'http://localhost:9090/api/v1/targets' | grep -o '\"health\":\"up\"'" \
        "up"
    
    # Check if metrics are in Prometheus
    test_check "Metrics in Prometheus" \
        "curl -s 'http://localhost:9090/api/v1/query?query=up' | grep -q 'result'"
else
    echo -e "${YELLOW}⚠️  Skipping Prometheus checks (metrics server not running)${NC}"
fi

echo ""
echo "📁 File System Check"
echo "-------------------"

# Check required files exist
test_check "docker-compose.observability.yml exists" "test -f docker-compose.observability.yml"
test_check "metrics_server.py exists" "test -f metrics_server.py"
test_check "start-observability.sh exists" "test -f start-observability.sh"
test_check "Prometheus config exists" "test -f observability/prometheus/prometheus.yml"
test_check "OTel config exists" "test -f observability/otel/collector-config.yml"
test_check "Filebeat config exists" "test -f observability/filebeat/filebeat.yml"
test_check "Grafana datasource exists" "test -f observability/grafana/provisioning/datasources/prometheus.yml"
test_check "Logs directory exists" "test -d logs"

echo ""
echo "🔍 Data Flow Check"
echo "-----------------"

# Check if traces are being generated
if [ -f "traces.jsonl" ]; then
    TRACE_COUNT=$(wc -l < traces.jsonl 2>/dev/null || echo "0")
    if [ "$TRACE_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✅ Traces file exists with $TRACE_COUNT entries${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠️  Traces file exists but is empty${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  No traces.jsonl found (run application to generate)${NC}"
fi

# Check if decision logs are being generated
if [ -f "decision_logs.jsonl" ]; then
    DECISION_COUNT=$(wc -l < decision_logs.jsonl 2>/dev/null || echo "0")
    if [ "$DECISION_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✅ Decision logs file exists with $DECISION_COUNT entries${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${YELLOW}⚠️  Decision logs file exists but is empty${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  No decision_logs.jsonl found (run application to generate)${NC}"
fi

echo ""
echo "📊 Summary"
echo "---------"
echo -e "  ${GREEN}✅ Passed: $PASSED${NC}"
echo -e "  ${RED}❌ Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "✅ Your observability stack is ready!"
    echo ""
    echo "Next steps:"
    echo "  1. Start metrics server: python metrics_server.py"
    echo "  2. Run application: python main.py"
    echo "  3. View dashboards:"
    echo "     • Grafana: http://localhost:3000"
    echo "     • Prometheus: http://localhost:9090"
    echo "     • Jaeger: http://localhost:16686"
    echo "     • Kibana: http://localhost:5601"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Start observability stack: ./start-observability.sh"
    echo "  2. Install dependencies: pip install -r requirements.txt"
    echo "  3. Check Docker is running: docker ps"
    exit 1
fi
