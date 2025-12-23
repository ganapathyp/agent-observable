.PHONY: install test test-unit test-integration run clean

install:
	@echo "Setting up virtual environment..."
	@if [ ! -d ".venv" ]; then \
		if command -v uv &> /dev/null; then \
			uv venv .venv; \
		else \
			python3 -m venv .venv; \
		fi \
	fi
	@if [ -f ".venv/bin/pip" ]; then \
		.venv/bin/pip install -r requirements.txt; \
		.venv/bin/pip install -e . || echo "Note: Package may already be installed"; \
	elif [ -f ".venv/bin/python3" ]; then \
		.venv/bin/python3 -m pip install -r requirements.txt 2>/dev/null || \
		(echo "Installing pip..." && .venv/bin/python3 -m ensurepip --upgrade && .venv/bin/python3 -m pip install -r requirements.txt); \
		.venv/bin/python3 -m pip install -e . || echo "Note: Package may already be installed"; \
	elif command -v uv &> /dev/null; then \
		uv pip install -r requirements.txt; \
		uv pip install -e . || echo "Note: Package may already be installed"; \
	else \
		echo "Error: Cannot install dependencies. Please install pip or uv."; \
		exit 1; \
	fi
	@echo "Verifying installation..."
	@.venv/bin/python3 -c "import taskpilot; print('✅ TaskPilot installed successfully')" || \
		(echo "⚠️  Package import failed. Try: source .venv/bin/activate && python3 -c 'import taskpilot'"; exit 1)

test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	@.venv/bin/python -m pytest tests/test_*.py -v --tb=short -k "not integration" --cov=src --cov-report=term-missing

test-coverage:
	@echo "Running tests with coverage report..."
	@.venv/bin/python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Coverage report generated:"
	@echo "  - Terminal: See above"
	@echo "  - HTML: htmlcov/index.html"
	@echo ""
	@echo "To view in VS Code/Cursor:"
	@echo "  1. Right-click htmlcov/index.html → 'Open With' → Browser"
	@echo "  2. Or use: code htmlcov/index.html"
	@echo "  3. Or install 'Live Preview' extension and use 'Show Preview'"

test-integration:
	@echo "Running integration tests..."
	@.venv/bin/python tests/test_integration.py

run:
	@.venv/bin/python main.py

clean:
	@rm -rf .venv
	@rm -rf *.egg-info
	@rm -rf __pycache__ .pytest_cache
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
