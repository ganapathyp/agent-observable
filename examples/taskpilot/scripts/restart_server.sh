#!/bin/bash
# Restart TaskPilot server with correct host binding

echo "🛑 Stopping existing TaskPilot server..."
pkill -f "python.*main.py.*server" || true
sleep 2

echo "✅ Starting TaskPilot server on 0.0.0.0:8000..."
cd "$(dirname "$0")/.."
python3 main.py --server --port 8000 &

sleep 3

echo "🔍 Verifying server is listening on all interfaces..."
if netstat -an | grep -q "\.8000.*LISTEN"; then
    echo "✅ Server is running"
    netstat -an | grep 8000 | grep LISTEN
else
    echo "❌ Server may not be running correctly"
    exit 1
fi

echo ""
echo "📊 Test metrics endpoint:"
curl -s http://localhost:8000/metrics | grep -E "(llm_cost_total|policy_violations_total)" | head -5

echo ""
echo "✅ Server restarted. Check Prometheus target status:"
echo "   http://localhost:9090/targets"
