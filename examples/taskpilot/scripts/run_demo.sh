#!/bin/bash
# Complete demo script: Start Docker, generate data, verify, and provide viewing instructions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Demo Data Generation & Verification"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Check Docker
echo "1️⃣  Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "   Please start Docker Desktop"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Step 2: Start Docker observability stack
echo "2️⃣  Starting Docker Observability Stack..."
cd "$PROJECT_DIR"

if docker ps | grep -q taskpilot-prometheus; then
    echo -e "${YELLOW}⚠️  Observability stack already running${NC}"
else
    echo "   Starting services..."
    docker-compose -f docker-compose.observability.yml up -d
    
    echo "   Waiting for services to start (30 seconds)..."
    sleep 30
    
    # Check services
    echo "   Verifying services..."
    SERVICES=("taskpilot-prometheus" "taskpilot-grafana" "taskpilot-jaeger" "taskpilot-elasticsearch" "taskpilot-kibana" "taskpilot-otel-collector")
    ALL_UP=true
    for service in "${SERVICES[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
            echo -e "   ${GREEN}✅ ${service}${NC}"
        else
            echo -e "   ${RED}❌ ${service} - NOT RUNNING${NC}"
            ALL_UP=false
        fi
    done
    
    if [ "$ALL_UP" = false ]; then
        echo -e "${YELLOW}⚠️  Some services failed to start. Check logs:${NC}"
        echo "   docker-compose -f docker-compose.observability.yml logs"
        exit 1
    fi
fi
echo ""

# Step 3: Generate demo data
echo "3️⃣  Generating Demo Data..."
cd "$PROJECT_DIR"
python3 "$SCRIPT_DIR/generate_demo_data.py"
echo ""

# Step 4: Wait for Filebeat to ship logs
echo "4️⃣  Waiting for Filebeat to ship logs to Elasticsearch (30 seconds)..."
sleep 30
echo ""

# Step 5: Verify data
echo "5️⃣  Verifying Data in Tools..."
python3 "$SCRIPT_DIR/verify_demo_data.py"
echo ""

# Step 6: Print viewing instructions
echo "6️⃣  Viewing Instructions"
echo "========================================"
echo ""
echo -e "${GREEN}✅ Demo data generated and verified!${NC}"
echo ""
echo "📊 View Data in Tools:"
echo ""
echo "   📈 GRAFANA (Metrics & Dashboards):"
echo "      http://localhost:3000"
echo "      Login: admin / admin"
echo "      Dashboard: Golden Signals LLM Production"
echo ""
echo "   📊 PROMETHEUS (Metrics Query):"
echo "      http://localhost:9090"
echo ""
echo "   🔍 JAEGER (Traces):"
echo "      http://localhost:16686"
echo "      Search: Service = taskpilot"
echo ""
echo "   📝 KIBANA (Logs):"
echo "      http://localhost:5601"
echo "      Index Pattern: taskpilot-logs-*"
echo ""
echo "   🔧 ELASTICSEARCH (Direct API):"
echo "      http://localhost:9200"
echo ""
echo "💡 Tips:"
echo "   - Wait 1-2 minutes after generation for all data to appear"
echo "   - Refresh Kibana index patterns if logs don't appear"
echo "   - Check Prometheus targets to ensure metrics are being scraped"
echo ""
echo "📸 Screenshots to Take:"
echo "   1. Grafana Dashboard showing cost metrics"
echo "   2. Jaeger trace hierarchy (workflow → agent → tool)"
echo "   3. Kibana Discover view with filtered logs"
echo "   4. Prometheus query results"
echo ""
