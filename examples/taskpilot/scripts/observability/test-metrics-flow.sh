#!/bin/bash
# Test metrics flow: generate data and verify it's visible

echo "🧪 Testing Metrics Flow"
echo "======================"
echo ""

# Step 1: Run main.py to generate metrics
echo "1️⃣  Running main.py to generate metrics..."
python main.py > /dev/null 2>&1
echo "   ✅ main.py completed"
echo ""

# Step 2: Check if metrics.json was created
echo "2️⃣  Checking for metrics.json..."
if [ -f "metrics.json" ]; then
    echo "   ✅ metrics.json exists"
    echo "   📊 Content:"
    cat metrics.json | python3 -m json.tool | head -20
else
    echo "   ❌ metrics.json not found"
fi
echo ""

# Step 3: Check metrics endpoint
echo "3️⃣  Checking metrics endpoint..."
METRICS=$(curl -s http://localhost:8001/metrics 2>/dev/null)
if [ -n "$METRICS" ]; then
    echo "   ✅ Metrics endpoint responding"
    echo "   📊 Sample metrics:"
    echo "$METRICS" | head -15
else
    echo "   ❌ Metrics endpoint not responding"
    echo "   💡 Make sure metrics_server.py is running:"
    echo "      python metrics_server.py"
fi
echo ""

# Step 4: Check Prometheus targets
echo "4️⃣  Checking Prometheus targets..."
PROM_STATUS=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); target=data['data']['activeTargets'][0] if data['data']['activeTargets'] else None; print('UP' if target and target['health'] == 'up' else 'DOWN')" 2>/dev/null)
if [ "$PROM_STATUS" = "UP" ]; then
    echo "   ✅ Prometheus target is UP"
else
    echo "   ⚠️  Prometheus target status: $PROM_STATUS"
    echo "   💡 Check: http://localhost:9090/targets"
fi
echo ""

echo "✅ Test complete!"
echo ""
echo "Next steps:"
echo "  1. Open Grafana: http://localhost:3000"
echo "  2. Go to Explore → Prometheus"
echo "  3. Query: workflow_runs"
echo ""
