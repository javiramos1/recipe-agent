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
	@echo "  make setup           Create virtual environment, install dependencies, create .env file"
	@echo ""
	@echo "Development:"
	@echo "  make dev             Start application (http://localhost:7777)"
	@echo "  make dev DEBUG=1     Start with debug output enabled"
	@echo "  make dev-bkg         Start application in background"
	@echo "  make run             Start application (production mode)"
	@echo "  make run DEBUG=1     Start with debug output enabled"
	@echo "  make stop            Stop running application server"
	@echo ""
	@echo "Queries (with auto-managed background server):"
	@echo "  make query Q=\"..\"                           Run stateful query (uses session memory)"
	@echo "  make query Q=\"..\" S=1                       Run stateless query (no session history)"
	@echo "  make query Q=\"..\" DEBUG=1                   Run with debug output enabled"
	@echo "  make query Q=\"..\" IMG=path/to/image.png    Include image for ingredient detection"
	@echo "  make query Q=\"..\" S=1 DEBUG=1              Run stateless with debug enabled"
	@echo "  make query Q=\"..\" IMG=images/pasta.png DEBUG=1  Test with image and debug"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run unit tests"
	@echo "  make eval            Run integration tests (requires API keys)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Remove cache files and temporary data"
	@echo "  make help            Show this help message"

# Check if venv exists, create if not
venv-check:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "✓ Virtual environment created"; \
	fi

# Setup: Create venv, install dependencies, create .env, setup Agent UI
setup: venv-check
	@echo "Installing Python dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo ""
	@echo "Setting up Agent UI..."
	@if [ ! -d "agent-ui" ]; then \
		echo "Creating Agent UI project..."; \
		npx create-agent-ui@latest > /dev/null 2>&1; \
		echo "✓ Agent UI project created"; \
	else \
		echo "✓ Agent UI project already exists"; \
	fi
	@if [ -d "agent-ui" ] && [ ! -d "agent-ui/node_modules" ]; then \
		echo "Installing Agent UI dependencies..."; \
		cd agent-ui && npm install --legacy-peer-deps > /dev/null 2>&1 && cd ..; \
		echo "✓ Agent UI dependencies installed"; \
	fi
	@if [ ! -f .env ]; then \
		echo ""; \
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
		echo ""; \
		echo "✓ .env file already exists"; \
		echo ""; \
		echo "Setup complete! Run: make dev"; \
	fi

# Development: Start both AgentOS backend and Agent UI frontend
dev: venv-check
	@if [ "$(DEBUG)" = "1" ] || [ "$(DEBUG)" = "true" ]; then \
		export AGNO_DEBUG=True; \
	fi; \
	bash scripts/start_services.sh $(PYTHON)

# Development background: Start in background using helper script
dev-bkg: venv-check
	@./scripts/start_bkg.sh $(PYTHON)

# Production: Start both AgentOS backend and Agent UI frontend (production mode)
run: venv-check
	@if [ "$(DEBUG)" = "1" ] || [ "$(DEBUG)" = "true" ]; then \
		export AGNO_DEBUG=True; \
	fi; \
	bash scripts/start_services.sh $(PYTHON)

# Stop: Kill all running services (backend and frontend)
stop:
	@bash scripts/stop_services.sh

# Ad hoc Query: Run a single query (auto-manages background server)
# Usage: make query Q="..." [S=1] [DEBUG=1] [IMG=path/to/image.png]
query: venv-check dev-bkg
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"<your query>\" [S=1] [DEBUG=1] [IMG=path/to/image.png]"; \
		echo ""; \
		echo "Options:"; \
		echo "  S=1             Run in stateless mode (no session history)"; \
		echo "  DEBUG=1         Enable debug output (see tool calls, LLM input/output, metrics)"; \
		echo "  IMG=path/file   Include image for ingredient detection"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make query Q=\"What can I make with chicken?\""; \
		echo "  make query Q=\"What can I make with chicken?\" S=1"; \
		echo "  make query Q=\"What can I make with chicken?\" DEBUG=1"; \
		echo "  make query Q=\"What can I make with this?\" IMG=images/pasta.png"; \
		echo "  make query Q=\"What can I make with this?\" IMG=images/pasta.png DEBUG=1"; \
		exit 1; \
	fi
	@if [ "$(DEBUG)" = "1" ] || [ "$(DEBUG)" = "true" ]; then \
		export AGNO_DEBUG=True; \
		if [ "$(S)" = "1" ]; then \
			echo "Running stateless ad hoc query (no session memory)..."; \
		else \
			echo "Running stateful ad hoc query (with session memory)..."; \
		fi; \
		if [ -n "$(IMG)" ]; then \
			echo "Image: $(IMG)"; \
		fi; \
		echo "Debug output enabled"; \
		echo ""; \
		sleep 1; \
		if [ "$(S)" = "1" ]; then \
			if [ -n "$(IMG)" ]; then \
				$(PYTHON) query.py --stateless --image $(IMG) "$(Q)"; \
			else \
				$(PYTHON) query.py --stateless "$(Q)"; \
			fi; \
		else \
			if [ -n "$(IMG)" ]; then \
				$(PYTHON) query.py --image $(IMG) "$(Q)"; \
			else \
				$(PYTHON) query.py "$(Q)"; \
			fi; \
		fi; \
	else \
		if [ "$(S)" = "1" ]; then \
			echo "Running stateless ad hoc query (no session memory)..."; \
		else \
			echo "Running stateful ad hoc query (with session memory)..."; \
		fi; \
		if [ -n "$(IMG)" ]; then \
			echo "Image: $(IMG)"; \
		fi; \
		echo ""; \
		sleep 1; \
		if [ "$(S)" = "1" ]; then \
			if [ -n "$(IMG)" ]; then \
				$(PYTHON) query.py --stateless --image $(IMG) "$(Q)"; \
			else \
				$(PYTHON) query.py --stateless "$(Q)"; \
			fi; \
		else \
			if [ -n "$(IMG)" ]; then \
				$(PYTHON) query.py --image $(IMG) "$(Q)"; \
			else \
				$(PYTHON) query.py "$(Q)"; \
			fi; \
		fi; \
	fi; \
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
