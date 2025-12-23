#!/bin/bash
# Start production-like observability stack

set -e

DOCKER_DIR="/Users/ganapathypichumani/dev/docker/taskpilot"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting Production-Like Observability Stack"
echo "================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi

# Check if configs exist in Docker directory
if [ ! -f "$DOCKER_DIR/prometheus/prometheus.yml" ]; then
    echo "⚠️  Docker configs not found in $DOCKER_DIR"
    echo "   Running setup script..."
    "$PROJECT_DIR/setup-docker-configs.sh"
    echo ""
fi

# Check if already running
if docker ps | grep -q taskpilot-prometheus; then
    echo "⚠️  Observability stack already running"
    echo ""
    echo "To restart:"
    echo "  docker-compose -f docker-compose.observability.yml down"
    echo "  ./start-observability.sh"
    echo ""
    exit 0
fi

# Check Docker file sharing (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 macOS detected"
    echo "   Ensure Docker Desktop has file sharing enabled for:"
    echo "   /Users/ganapathypichumani/dev/docker"
    echo ""
fi

# Start services
echo "📊 Starting services..."
docker-compose -f docker-compose.observability.yml up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start (this may take 30-60 seconds)..."
sleep 15

# Check service health
echo ""
echo "🔍 Checking service health..."

check_service() {
    local name=$1
    local url=$2
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "  ✅ $name: Running"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    echo "  ⚠️  $name: Starting (may take a moment longer)"
    return 1
}

check_service "Prometheus" "http://localhost:9090/-/healthy" || true
check_service "Grafana" "http://localhost:3000/api/health" || true
check_service "Jaeger" "http://localhost:16686" || true
check_service "Kibana" "http://localhost:5601/api/status" || true

echo ""
echo "✅ Observability stack started!"
echo ""
echo "📊 Access Points:"
echo "  📈 Grafana:     http://localhost:3000 (admin/admin)"
echo "  📊 Prometheus:  http://localhost:9090"
echo "  🔍 Jaeger:      http://localhost:16686"
echo "  📋 Kibana:      http://localhost:5601"
echo ""
echo "💡 Next Steps:"
echo "  1. Start metrics server: python metrics_server.py"
echo "  2. Start your application: python main.py"
echo "  3. Open Grafana: http://localhost:3000"
echo "  4. View traces in Jaeger: http://localhost:16686"
echo "  5. View logs in Kibana: http://localhost:5601"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.observability.yml down"
echo ""
