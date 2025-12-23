#!/bin/bash
# Setup Docker configs in /Users/ganapathypichumani/dev/docker/taskpilot

set -e

DOCKER_DIR="/Users/ganapathypichumani/dev/docker/taskpilot"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Setting up Docker configs"
echo "=============================="
echo ""
echo "Docker directory: $DOCKER_DIR"
echo "Project directory: $PROJECT_DIR"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$DOCKER_DIR"/{prometheus,otel,filebeat,grafana/provisioning/{datasources,dashboards},logs}

# Copy config files
echo "📋 Copying configuration files..."

# Prometheus
cp "$PROJECT_DIR/observability/prometheus/prometheus.yml" "$DOCKER_DIR/prometheus/prometheus.yml"
echo "  ✅ Prometheus config copied"

# OpenTelemetry
cp "$PROJECT_DIR/observability/otel/collector-config.yml" "$DOCKER_DIR/otel/collector-config.yml"
echo "  ✅ OpenTelemetry config copied"

# Filebeat
cp "$PROJECT_DIR/observability/filebeat/filebeat.yml" "$DOCKER_DIR/filebeat/filebeat.yml"
echo "  ✅ Filebeat config copied"

# Grafana provisioning
cp -r "$PROJECT_DIR/observability/grafana/provisioning/"* "$DOCKER_DIR/grafana/provisioning/"
echo "  ✅ Grafana provisioning copied"

# Create logs directory
mkdir -p "$DOCKER_DIR/logs"
touch "$DOCKER_DIR/logs/.gitkeep"
echo "  ✅ Logs directory created"

echo ""
echo "✅ Docker configs setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Configure Docker Desktop file sharing:"
echo "     - Open Docker Desktop → Settings → Resources → File Sharing"
echo "     - Add: /Users/ganapathypichumani/dev/docker"
echo "     - Click 'Apply & Restart'"
echo ""
echo "  2. Start observability stack:"
echo "     ./start-observability.sh"
echo ""
