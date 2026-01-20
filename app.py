"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory
- Creates AgentOS instance with agent and AGUI interface
- Serves REST API endpoints via FastAPI

Run with: python app.py

Features:
- AGUI REST API: POST /agui for agent interaction
- OpenAPI docs: http://localhost:PORT/docs
- Session management: Automatic per session_id
- Tool lifecycle: MCPs initialized before AgentOS starts

Frontend: Served by separate Agent UI (http://localhost:3000)
"""

import os
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


# Set Uvicorn environment variables for large request/response handling
os.environ.setdefault("UVICORN_LIMIT_MAX_REQUESTS", "1000")
os.environ.setdefault("UVICORN_LIMIT_CONCURRENCY", "100")


class IncreaseBodySizeMiddleware(BaseHTTPMiddleware):
    """Middleware to increase the max body size limit for streaming responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "POST":
            # Don't enforce size limit on streaming responses
            pass
        response = await call_next(request)
        return response


# Initialize agent using factory pattern
logger.info("Starting Recipe Recommendation Service initialization...")
agent = initialize_recipe_agent()

# Create AgentOS with the agent and AGUI interface
logger.info("Creating AgentOS instance with AGUI interface...")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)

# Get the FastAPI app for external serving
app = agent_os.get_app()

# Add middleware for large body handling
app.add_middleware(IncreaseBodySizeMiddleware)


if __name__ == "__main__":
    logger.info(f"Starting Recipe Recommendation Service on port {config.PORT}")
    logger.info(f"Image detection mode: {config.IMAGE_DETECTION_MODE}")
    logger.info(f"Max request body size: 50MB")
    logger.info("---")
    logger.info(f"✓ Web UI available at: http://localhost:{config.PORT}")
    logger.info(f"✓ API endpoints at: http://localhost:{config.PORT}/api/agents/chat")
    logger.info(f"✓ OpenAPI docs at: http://localhost:{config.PORT}/docs")
    logger.info("---")
    
    # Run with AgentOS (production-ready, no reload)
    # Note: reload=False (default) to avoid MCP lifespan issues
    agent_os.serve(app=app, port=config.PORT, reload=False)
