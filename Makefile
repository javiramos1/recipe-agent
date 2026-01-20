.PHONY: setup dev dev-bkg run query stop test eval clean clean-memories help venv-check

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
	@echo "  make dev             Start backend server (http://localhost:7777)"
	@echo "  make dev-bkg         Start backend server in background"
	@echo "  make run             Start backend server (production mode)"
	@echo "  make stop            Stop running backend server"
	@echo ""
	@echo "Queries (with auto-managed background server):"
	@echo "  make query Q=\"..\"                           Run stateful query (uses session memory)"
	@echo "  make query Q=\"..\" S=1                       Run stateless query (no session history)"
	@echo "  make query Q=\"..\" IMG=path/to/image.png    Include image for ingredient detection"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run unit tests"
	@echo "  make eval            Run integration tests (requires API keys)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Remove cache files and temporary data"
	@echo "  make clean-memories  Clear all user memories from database"
	@echo "  make help            Show this help message"

# Check if venv exists, create if not
venv-check:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "✓ Virtual environment created"; \
	fi

# Setup: Create venv, install dependencies, create .env
setup: venv-check
	@echo "Installing Python dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
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

# Development: Start AgentOS backend
dev: venv-check
	@$(PYTHON) app.py

# Development background: Start in background
dev-bkg: venv-check
	@nohup $(PYTHON) app.py > /tmp/agent_server.log 2>&1 &
	@echo "Backend server started in background (PID: $$!)"
	@echo "Logs: tail -f /tmp/agent_server.log"
	@sleep 3
	@curl -s http://localhost:7777/health > /dev/null && echo "✓ Server is responding" || echo "⚠ Server may still be starting..."

# Production: Start AgentOS backend
run: venv-check
	@$(PYTHON) app.py

# Stop: Kill all running backend processes
stop:
	@pkill -f "python app.py" || true
	@echo "✓ Server stopped"

# Ad hoc Query: Run a single query (auto-manages background server)
# Usage: make query Q="..." [S=1] [IMG=path/to/image.png]
query: venv-check dev-bkg
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"<your query>\" [S=1] [IMG=path/to/image.png]"; \
		echo ""; \
		echo "Options:"; \
		echo "  S=1             Run in stateless mode (no session history)"; \
		echo "  IMG=path/file   Include image for ingredient detection"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make query Q=\"What can I make with chicken?\""; \
		echo "  make query Q=\"What can I make with chicken?\" S=1"; \
		echo "  make query Q=\"What can I make with this?\" IMG=images/pasta.png"; \
		exit 1; \
	fi
	@sleep 1; \
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

# Clean Memories: Clear all user memories from database
clean-memories:
	@if [ ! -f agno.db ]; then \
		echo "No database found (agno.db). Nothing to clean."; \
		exit 0; \
	fi
	@echo "Clearing user memories from database..."
	@sqlite3 agno.db "DELETE FROM agno_memories;"
	@COUNT=$$(sqlite3 agno.db "SELECT COUNT(*) FROM agno_memories;"); \
	if [ "$$COUNT" -eq 0 ]; then \
		echo "✓ All memories cleared (0 records remaining)"; \
	else \
		echo "⚠ Unexpected records found: $$COUNT"; \
	fi
