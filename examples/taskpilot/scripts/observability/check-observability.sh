#!/bin/bash
# Check observability stack status

echo "🔍 Observability Stack Status Check"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Docker
echo "1️⃣  Docker Status"
echo "----------------"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed${NC}"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "   Start Docker Desktop"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Check services
echo "2️⃣  Docker Services Status"
echo "---------------------------"
SERVICES=("taskpilot-prometheus" "taskpilot-grafana" "taskpilot-jaeger" "taskpilot-elasticsearch" "taskpilot-kibana" "taskpilot-otel-collector")

ALL_RUNNING=true
for service in "${SERVICES[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
        STATUS=$(docker ps --filter "name=${service}" --format "{{.Status}}")
        echo -e "${GREEN}✅ ${service}${NC} - ${STATUS}"
    else
        echo -e "${RED}❌ ${service} - NOT RUNNING${NC}"
        ALL_RUNNING=false
    fi
done

echo ""

if [ "$ALL_RUNNING" = false ]; then
    echo -e "${YELLOW}⚠️  Some services are not running${NC}"
    echo ""
    echo "To start services:"
    echo "  ./start-observability.sh"
    echo ""
fi

# Check endpoints
echo "3️⃣  Service Endpoints"
echo "--------------------"

check_endpoint() {
    local name=$1
    local url=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${name}${NC} - ${url}"
        return 0
    else
        echo -e "${RED}❌ ${name}${NC} - ${url} (not accessible)"
        return 1
    fi
}

check_endpoint "Grafana" "http://localhost:3000/api/health" || true
check_endpoint "Prometheus" "http://localhost:9090/-/healthy" || true
check_endpoint "Jaeger" "http://localhost:16686" || true
check_endpoint "Kibana" "http://localhost:5601/api/status" || true
check_endpoint "Elasticsearch" "http://localhost:9200" || true

echo ""

# Check metrics server
echo "4️⃣  Metrics Server"
echo "------------------"
if curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Metrics server running on port 8001${NC}"
    echo "   http://localhost:8001/metrics"
elif curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Metrics server running on port 8000${NC}"
    echo "   http://localhost:8000/metrics"
else
    echo -e "${RED}❌ Metrics server not running${NC}"
    echo "   Start with: python metrics_server.py"
fi

echo ""

# Summary
echo "📊 Summary"
echo "----------"
RUNNING_COUNT=$(docker ps --format "{{.Names}}" | grep -c taskpilot- || echo "0")
echo "Running services: ${RUNNING_COUNT}/6"

if [ "$RUNNING_COUNT" -eq 6 ]; then
    echo -e "${GREEN}✅ All services are running!${NC}"
    echo ""
    echo "Access dashboards:"
    echo "  📈 Grafana:     http://localhost:3000 (admin/admin)"
    echo "  📊 Prometheus:  http://localhost:9090"
    echo "  🔍 Jaeger:      http://localhost:16686"
    echo "  📋 Kibana:      http://localhost:5601"
else
    echo -e "${YELLOW}⚠️  Not all services are running${NC}"
    echo ""
    echo "To start: ./start-observability.sh"
fi

echo ""
