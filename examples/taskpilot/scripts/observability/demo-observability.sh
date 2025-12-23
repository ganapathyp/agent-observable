#!/bin/bash
# Demo script for team advocacy

echo "🎯 Production-Like Observability Demo"
echo "======================================"
echo ""

# 1. Show architecture
echo "📐 Architecture:"
echo "  • Prometheus: Metrics collection"
echo "  • Grafana: Visualization dashboards"
echo "  • OpenTelemetry: Distributed tracing"
echo "  • Jaeger: Trace visualization"
echo "  • Elasticsearch + Kibana: Log aggregation"
echo ""

# 2. Show it's running
echo "✅ Services Status:"
if command -v docker &> /dev/null; then
    docker-compose -f docker-compose.observability.yml ps 2>/dev/null || echo "  ⚠️  Services not running. Run: ./start-observability.sh"
else
    echo "  ⚠️  Docker not found"
fi
echo ""

# 3. Show access points
echo "🌐 Access Points:"
echo "  📈 Grafana:     http://localhost:3000 (admin/admin)"
echo "  📊 Prometheus:  http://localhost:9090"
echo "  🔍 Jaeger:      http://localhost:16686"
echo "  📋 Kibana:      http://localhost:5601"
echo ""

# 4. Open dashboards (if on macOS/Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🚀 Opening dashboards..."
    open http://localhost:3000 2>/dev/null || true
    open http://localhost:16686 2>/dev/null || true
    open http://localhost:5601 2>/dev/null || true
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🚀 Opening dashboards..."
    xdg-open http://localhost:3000 2>/dev/null || true
    xdg-open http://localhost:16686 2>/dev/null || true
    xdg-open http://localhost:5601 2>/dev/null || true
else
    echo "💡 Please open dashboards manually in your browser"
fi

echo ""
echo "💡 Key Benefits:"
echo "  ✅ Production-like environment"
echo "  ✅ 100% free/open-source"
echo "  ✅ One-command setup"
echo "  ✅ Reusable template"
echo "  ✅ Complete observability"
echo ""
