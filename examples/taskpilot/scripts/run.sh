#!/bin/bash
# Run taskpilot using its isolated venv

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Use uv if available (recommended)
if command -v uv &> /dev/null; then
    # Ensure venv exists
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment with uv..."
        uv venv .venv
    fi
    
    # Install dependencies if needed
    if [ ! -f ".venv/.installed" ]; then
        echo "Installing dependencies..."
        uv pip install --python .venv/bin/python -r requirements.txt
        uv pip install --python .venv/bin/python -e .
        touch .venv/.installed
    fi
    
    # Run main.py from taskpilot directory
    # Package is installed in venv, so imports work directly
    cd "$SCRIPT_DIR"
    "$VENV_DIR/bin/python" main.py "$@"
else
    # Fallback to manual venv
    VENV_DIR=".venv"
    
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
        "$VENV_DIR/bin/pip" install -r requirements.txt
        "$VENV_DIR/bin/pip" install -e .
    fi
    
    # Activate venv and run main.py
    cd "$SCRIPT_DIR"
    source "$VENV_DIR/bin/activate"
    python main.py "$@"
fi
