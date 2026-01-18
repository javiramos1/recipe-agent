.PHONY: setup dev run test eval clean help

# Default target
help:
	@echo "Recipe Recommendation Service - Development Commands"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make setup       Install dependencies and create .env file"
	@echo ""
	@echo "Development:"
	@echo "  make dev         Start application (http://localhost:7777)"
	@echo "  make run         Start application (production mode)"
	@echo ""
	@echo "Testing:"
	@echo "  make test        Run unit tests"
	@echo "  make eval        Run integration tests (requires API keys)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       Remove cache files and temporary data"
	@echo "  make help        Show this help message"

# Setup: Install dependencies and create .env
setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
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
dev:
	@echo "Starting application in development mode..."
	@echo ""
	@echo "Web UI (AGUI):     http://localhost:7777"
	@echo "REST API:          http://localhost:7777/api/agents/chat"
	@echo "OpenAPI Docs:      http://localhost:7777/docs"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo ""
	python app.py

# Production: Start without hot-reload
run:
	@echo "Starting application in production mode..."
	@echo ""
	@echo "Web UI (AGUI):     http://localhost:7777"
	@echo "REST API:          http://localhost:7777/api/agents/chat"
	@echo "OpenAPI Docs:      http://localhost:7777/docs"
	@echo ""
	python app.py

# Unit Tests
test:
	@echo "Running unit tests..."
	@echo ""
	pytest tests/unit/ -v --tb=short
	@echo ""
	@echo "✓ Unit tests complete"

# Integration Tests (requires valid API keys)
eval:
	@echo "Running integration tests..."
	@echo ""
	@echo "Note: These tests require valid GEMINI_API_KEY and SPOONACULAR_API_KEY"
	@echo ""
	pytest tests/integration/ -v --tb=short
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
	@echo "✓ Clean complete"
