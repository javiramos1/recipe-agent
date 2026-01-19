.PHONY: setup dev dev-bkg run query stop test eval clean help venv-check

# Virtual environment directory
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# Default target
help:
	@echo "Recipe Recommendation Service - Development Commands"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make setup       Create virtual environment, install dependencies, create .env file"
	@echo ""
	@echo "Development:"
	@echo "  make dev         Start application (http://localhost:7777)"
	@echo "  make dev-bkg     Start application in background"
	@echo "  make run         Start application (production mode)"
	@echo "  make stop        Stop running application server"
	@echo "  make query Q=\"..\"  Run ad hoc query (auto-starts/stops background server)"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run unit tests"
	@echo "  make eval        Run integration tests (requires API keys)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       Remove cache files and temporary data"
	@echo "  make help        Show this help message"

# Check if venv exists, create if not
venv-check:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "✓ Virtual environment created"; \
	fi

# Setup: Create venv, install dependencies, create .env
setup: venv-check
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo ""; \
		echo "✓ .env file created"; \
		echo ""; \
		echo "Next steps:"; \
		echo "  1. Edit .env and add your API keys:"; \
		echo "     - GEMINI_API_KEY (from Google Cloud Console)"; \
		echo "     - SPOONACULAR_API_KEY (from spoonacular.com/food-api)"; \
		echo ""; \
		echo "  2. Run: make dev"; \
	else \
		echo "✓ .env file already exists"; \
	fi

# Development: Start with hot-reload
dev: venv-check
	@echo "Starting application in development mode..."
	@echo ""
	@echo "Web UI (AGUI):     http://localhost:7777"
	@echo "REST API:          http://localhost:7777/api/agents/chat"
	@echo "OpenAPI Docs:      http://localhost:7777/docs"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo ""
	$(PYTHON) app.py

# Development background: Start in background using helper script
dev-bkg: venv-check
	@./scripts/start_bkg.sh $(PYTHON)

# Production: Start without hot-reload
run: venv-check
	@echo "Starting application in production mode..."
	@echo ""
	@echo "Web UI (AGUI):     http://localhost:7777"
	@echo "REST API:          http://localhost:7777/api/agents/chat"
	@echo "OpenAPI Docs:      http://localhost:7777/docs"
	@echo ""
	$(PYTHON) app.py

# Stop: Kill any running app.py processes
stop:
	@pkill -f "python app.py" 2>/dev/null || true
	@echo "✓ Application stopped"

# Ad hoc Query: Run a single query (auto-manages background server)
query: venv-check dev-bkg
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"<your query>\""; \
		echo "Example: make query Q=\"What can I make with chicken and rice?\""; \
		exit 1; \
	fi
	@echo "Running ad hoc query..."
	@echo ""
	@sleep 1; \
	$(PYTHON) query.py $(Q); \
	QUERY_RESULT=$$?; \
	echo ""; \
	echo "Stopping background server..."; \
	make stop; \
	exit $$QUERY_RESULT

# Unit Tests
test: venv-check
	@echo "Running unit tests..."
	@echo ""
	$(PYTHON) -m pytest tests/unit/ -v --tb=short
	@echo ""
	@echo "✓ Unit tests complete"

# Integration Tests (requires valid API keys)
eval: venv-check
	@echo "Running integration tests..."
	@echo ""
	@echo "Note: These tests require valid GEMINI_API_KEY and SPOONACULAR_API_KEY"
	@echo ""
	$(PYTHON) -m pytest tests/integration/ -v --tb=short
	@echo ""
	@echo "✓ Integration tests complete"

# Clean: Remove cache and temporary files
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Clean complete"
