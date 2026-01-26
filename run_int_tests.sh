#!/bin/bash
# Helper script to run integration tests with disabled knowledge/memory features

set -e

cd "$(dirname "$0")"

echo "Running REST API integration tests..."
echo ""

# Kill any existing app processes
echo "Stopping any running app instances..."
pkill -f "python app.py" 2>/dev/null || true
sleep 2

echo "Starting app with knowledge graph, memories, and Spoonacular disabled..."

# Start app with disabled features
export OUTPUT_FORMAT=json
export LOG_LEVEL=DEBUG
export SEARCH_KNOWLEDGE=false
export UPDATE_KNOWLEDGE=false
export ENABLE_USER_MEMORIES=false
export ENABLE_SESSION_SUMMARIES=false
export USE_SPOONACULAR=false

.venv/bin/python app.py > /tmp/recipe_service_test.log 2>&1 &
APP_PID=$!
echo "App started with PID: $APP_PID"

# Wait for app to be ready (with health check)
echo "Waiting for app to be ready..."
MAX_WAIT=20
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:7777/docs >/dev/null 2>&1; then
        echo "✓ App is ready on http://localhost:7777"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $ELAPSED -eq $MAX_WAIT ]; then
    echo "✗ App failed to start within $MAX_WAIT seconds"
    echo "Last 50 lines of app log:"
    tail -50 /tmp/recipe_service_test.log
    exit 1
fi

# Additional wait for API endpoint to be fully ready
echo "Waiting for API endpoint to warm up..."
sleep 3

echo ""
echo "Running tests..."
echo ""

# Run tests
.venv/bin/python -m pytest tests/integration/test_integration.py -v --tb=short
TEST_RESULT=$?

echo ""
echo "Stopping test app (PID $APP_PID)..."
kill $APP_PID 2>/dev/null || true
sleep 1

if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ REST API integration tests complete"
else
    echo "✗ Some tests failed"
fi

exit $TEST_RESULT
