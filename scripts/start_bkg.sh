#!/bin/bash
# Helper script to start the app in background

set -e

PYTHON_CMD="$1"
VENV_DIR=".venv"

if pgrep -f "python app.py" > /dev/null 2>&1; then
    echo "✓ Application already running (PID: $(pgrep -f 'python app.py'))"
else
    echo "Starting application in background..."
    nohup "$PYTHON_CMD" app.py > /tmp/recipe_service.log 2>&1 &
    sleep 3
    if pgrep -f "python app.py" > /dev/null 2>&1; then
        echo "✓ Application started (PID: $(pgrep -f 'python app.py'))"
        echo "  → http://localhost:7777"
    else
        echo "✗ Failed to start. Logs:"
        tail -10 /tmp/recipe_service.log 2>/dev/null || echo "(no logs)"
        exit 1
    fi
fi
