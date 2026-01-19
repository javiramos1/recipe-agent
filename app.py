"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory (async)
- Creates AgentOS instance with agent
- Serves REST API and Web UI automatically via AgentOS

Run with: python app.py

Features:
- REST API endpoints: POST /api/agents/chat, GET /api/agents/{session_id}/history
- Web UI (AGUI): ChatGPT-like interface at http://localhost:PORT
- OpenAPI docs: http://localhost:PORT/docs
- Session management: Automatic per session_id
- Tool lifecycle: MCPs initialized before AgentOS starts (async initialization)
"""

import asyncio

from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

from config import config
from logger import logger
from agent import initialize_recipe_agent


# Initialize agent using factory pattern (async)
logger.info("Starting Recipe Recommendation Service initialization...")
agent = asyncio.run(initialize_recipe_agent())

# Create AgentOS with the agent and Web UI interface
logger.info("Creating AgentOS instance with Web UI...")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)

# Get the FastAPI app for external serving (e.g., Docker)
app = agent_os.get_app()


if __name__ == "__main__":
    logger.info(f"Starting Recipe Recommendation Service on port {config.PORT}")
    logger.info(f"Image detection mode: {config.IMAGE_DETECTION_MODE}")
    logger.info("---")
    logger.info(f"✓ Web UI available at: http://localhost:{config.PORT}")
    logger.info(f"✓ API endpoints at: http://localhost:{config.PORT}/api/agents/chat")
    logger.info(f"✓ OpenAPI docs at: http://localhost:{config.PORT}/docs")
    logger.info("---")
    
    # Run with AgentOS (production-ready, no reload)
    # Note: reload=False (default) to avoid MCP lifespan issues
    agent_os.serve(app="app:app", port=config.PORT, reload=False)
