#!/bin/bash
# Kill process using port 8000

echo "🔍 Finding process on port 8000..."

PID=$(lsof -ti :8000)

if [ -z "$PID" ]; then
    echo "✅ Port 8000 is free"
    exit 0
fi

echo "Found process: PID $PID"
lsof -i :8000

read -p "Kill this process? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    kill -9 $PID
    echo "✅ Killed process $PID"
    echo "Port 8000 is now free"
else
    echo "⚠️  Process not killed. Use port 8001 for metrics server instead."
    echo "   Set: export METRICS_PORT=8001"
fi
