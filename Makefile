.PHONY: setup dev debug dev-bkg run query stop test eval int-tests lint format clean clean-memories zip help venv-check

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
	@echo "  make dev             Start backend server (http://localhost:7777, debug log level)"
	@echo "  make debug           Start backend server with full debug mode (log level + agent debug + debug level 2)"
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
	@echo "  make eval            Run integration evals (Agno evals framework, requires API keys)"
	@echo "  make int-tests       Run REST API integration tests (requires running app)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            Run Ruff and Flake8 linters"
	@echo "  make format          Fix formatting issues with Ruff"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean           Remove cache files and temporary data"
	@echo "  make clean-memories  Clear ALL user memories, sessions, knowledge, and learnings"
	@echo "  make zip             Create a ZIP archive of source code (excludes files in .gitignore)"
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

# Development: Start AgentOS backend (with debug logging, json output format)
dev: venv-check
	@LOG_LEVEL=DEBUG OUTPUT_FORMAT=json $(PYTHON) app.py

# Debug: Start with full debug mode (debug logging + agent debug mode + debug level 2, json output format)
debug: venv-check
	@LOG_LEVEL=DEBUG OUTPUT_FORMAT=json DEBUG_MODE=1 DEBUG_LEVEL=2 $(PYTHON) app.py

# Development background: Start in background (json output format)
dev-bkg: venv-check
	@nohup env OUTPUT_FORMAT=json LOG_LEVEL=DEBUG $(PYTHON) app.py > /tmp/recipe_service.log 2>&1 &
	@sleep 2
	@pgrep -f "python app.py" > /dev/null && echo "✓ Backend started (http://localhost:7777)" || echo "⚠ Check logs: tail -f /tmp/recipe_service.log"

# Production: Start AgentOS backend (markdown output format for UI rendering)
run: venv-check
	@OUTPUT_FORMAT=markdown $(PYTHON) app.py

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

# Integration Evals (Agno evals framework - requires valid API keys)
# Note: To view evals in the UI, start AgentOS first (make dev) in a separate terminal
eval: venv-check
	@echo "Running integration evals (Agno evals framework)..."
	@echo ""
	@echo "VIEWING EVALS IN UI:"
	@echo "  1. Start AgentOS in separate terminal: make dev"
	@echo "  2. Run this command: make eval"
	@echo "  3. Connect os.agno.com to http://localhost:7777"
	@echo "  4. View eval results in 'Evaluations' tab"
	@echo ""
	@echo "Note: These tests require valid GEMINI_API_KEY and SPOONACULAR_API_KEY"
	@echo ""
	$(PYTHON) -m pytest tests/integration/test_eval.py -v --tb=short
	@echo ""
	@echo "✓ Integration evals complete"
	@echo ""
	@echo "To view results in UI: Connect os.agno.com to http://localhost:7777"

# REST API Integration Tests (starts app with knowledge/memory disabled for clean testing)
int-tests: venv-check
	@bash run_int_tests.sh

# Lint: Run Ruff and Flake8 linters
lint: venv-check
	@echo "Running Ruff linter..."
	@$(PYTHON) -m ruff check src tests app.py query.py --line-length=120 || true
	@echo ""
	@echo "Running Flake8 linter..."
	@$(PYTHON) -m flake8 src tests app.py query.py || true
	@echo ""
	@echo "✓ Linting complete"

# Format: Fix formatting issues with Ruff
format: venv-check
	@echo "Fixing formatting issues with Ruff..."
	@$(PYTHON) -m ruff format src tests app.py query.py --line-length=120
	@echo ""
	@echo "✓ Formatting complete"

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

# Clean Memories: Clear all user memories, sessions, knowledge, and learnings from all databases
clean-memories:
	@echo "Clearing all user data (memories, sessions, knowledge, learnings)..."
	@if [ -f agno.db ]; then \
		echo "  - Clearing agno_memories table..."; \
		sqlite3 agno.db "DELETE FROM agno_memories;"; \
		echo "  - Clearing agno_sessions table..."; \
		sqlite3 agno.db "DELETE FROM agno_sessions;"; \
		echo "  - Clearing agno_knowledge table..."; \
		sqlite3 agno.db "DELETE FROM agno_knowledge;"; \
		echo "  - Clearing agno_learnings table..."; \
		sqlite3 agno.db "DELETE FROM agno_learnings;"; \
		MEMORIES=$$(sqlite3 agno.db "SELECT COUNT(*) FROM agno_memories;"); \
		SESSIONS=$$(sqlite3 agno.db "SELECT COUNT(*) FROM agno_sessions;"); \
		KNOWLEDGE=$$(sqlite3 agno.db "SELECT COUNT(*) FROM agno_knowledge;"); \
		LEARNINGS=$$(sqlite3 agno.db "SELECT COUNT(*) FROM agno_learnings;"); \
		echo "✓ agno.db cleared (memories: $$MEMORIES, sessions: $$SESSIONS, knowledge: $$KNOWLEDGE, learnings: $$LEARNINGS)"; \
	else \
		echo "⚠ agno.db not found"; \
	fi
	@if [ -f tmp/recipe_agent_sessions.db ]; then \
		echo "  - Deleting session database..."; \
		rm -f tmp/recipe_agent_sessions.db; \
		echo "✓ Session database deleted"; \
	fi
	@if [ -d tmp/lancedb ]; then \
		echo "  - Deleting knowledge graph (vector DB)..."; \
		rm -rf tmp/lancedb; \
		echo "✓ Knowledge graph deleted"; \
	fi
	@if [ -f agno_traces.db ]; then \
		echo "  - Deleting traces database..."; \
		rm -f agno_traces.db; \
		echo "✓ Traces database deleted"; \
	fi
	@echo ""
	@echo "✓ All user data cleared successfully"
	@echo ""
	@echo "Next step: Restart the server (make dev or make run)"

# Zip: Create a ZIP archive of source code excluding files in .gitignore
zip: lint
	@echo "Creating ZIP archive..."
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	ZIPFILE="recipe-agent_$$TIMESTAMP.zip"; \
	git archive --format=zip --output="$$ZIPFILE" HEAD && \
	SIZE=$$(du -h "$$ZIPFILE" | cut -f1); \
	echo "✓ ZIP archive created: $$ZIPFILE ($$SIZE)"
