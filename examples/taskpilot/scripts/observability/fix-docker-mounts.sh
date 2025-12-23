#!/bin/bash
# Fix Docker mount issues - Configure Docker Desktop file sharing

echo "🔧 Docker Mount Fix for macOS"
echo "=============================="
echo ""

DOCKER_DIR="/Users/ganapathypichumani/dev/docker"

echo "📋 Docker Desktop File Sharing Configuration"
echo "--------------------------------------------"
echo ""
echo "To fix mount issues, configure Docker Desktop:"
echo ""
echo "1. Open Docker Desktop"
echo "2. Go to Settings (gear icon) → Resources → File Sharing"
echo "3. Add this path:"
echo ""
echo "   $DOCKER_DIR"
echo ""
echo "4. Click 'Apply & Restart'"
echo "5. Wait for Docker to restart (~30 seconds)"
echo ""
echo "After configuring, run: ./start-observability.sh"
echo ""

# Check if directory exists
if [ ! -d "$DOCKER_DIR" ]; then
    echo "⚠️  Docker directory doesn't exist: $DOCKER_DIR"
    echo "   Creating it..."
    mkdir -p "$DOCKER_DIR"
    echo "   ✅ Created"
    echo ""
fi

# Run setup script
if [ -f "setup-docker-configs.sh" ]; then
    echo "📋 Setting up Docker configs..."
    ./setup-docker-configs.sh
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "Next: Configure Docker Desktop file sharing (see above)"
echo "Then: ./start-observability.sh"
