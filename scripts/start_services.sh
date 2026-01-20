#!/bin/bash
# Start both AgentOS backend and Agent UI frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="$1"

# Colors for output
PURPLE='\033[0;35m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start AgentOS backend
echo -e "${PURPLE}╔════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║     Starting Recipe Recommendation     ║${NC}"
echo -e "${PURPLE}║         Service with Agent UI          ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}[1/2] Starting AgentOS backend...${NC}"
cd "$PROJECT_ROOT"
"$PYTHON" app.py &
BACKEND_PID=$!
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${YELLOW}✗ Backend failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}[2/2] Starting Agent UI frontend...${NC}"
cd "$PROJECT_ROOT"

# Check if agent-ui directory exists, if not create it
if [ ! -d "agent-ui" ]; then
    echo -e "${YELLOW}Agent UI not found, setting up...${NC}"
    npx create-agent-ui@latest > /dev/null 2>&1 || true
fi

cd "$PROJECT_ROOT/agent-ui"
npm run dev &
FRONTEND_PID=$!
sleep 5

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${YELLOW}✗ Frontend failed to start${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Display startup complete message
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        🚀 Services Started! 🚀        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Web Interface:${NC}"
echo -e "  🎨 Agent UI:      ${PURPLE}http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}Backend Services:${NC}"
echo -e "  🔌 AgentOS API:   ${PURPLE}http://localhost:7777${NC}"
echo -e "  📚 API Docs:      ${PURPLE}http://localhost:7777/docs${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open ${PURPLE}http://localhost:3000${NC} in your browser"
echo "  2. The endpoint should be pre-configured to ${PURPLE}http://localhost:7777${NC}"
echo "  3. Start chatting with your recipe agent!"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for both processes
wait
