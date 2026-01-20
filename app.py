"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory (async)
- Initializes tracing with dedicated database
- Creates AgentOS instance for REST API with tracing enabled
- Serves recipe recommendation endpoints

Run with: python app.py
"""

import asyncio

from agno.os import AgentOS

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


# Initialize agent and tracing using async factory pattern
logger.info("Starting Recipe Recommendation Service initialization...")

# Run async initialization at startup
agent, tracing_db = asyncio.run(initialize_recipe_agent())

# Create AgentOS with the agent and tracing enabled (if configured)
logger.info("Creating AgentOS instance...")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    tracing=config.ENABLE_TRACING,
    tracing_db=tracing_db if tracing_db else None,
)

# Get the FastAPI app for external serving
app = agent_os.get_app()

if __name__ == "__main__":
    logger.info(f"Starting Recipe Recommendation Service on port {config.PORT}")
    logger.info(f"Image detection mode: {config.IMAGE_DETECTION_MODE}")
    logger.info("---")
    logger.info(f"✓ API endpoints at: http://localhost:{config.PORT}/api/agents/chat")
    logger.info(f"✓ OpenAPI docs at: http://localhost:{config.PORT}/docs")
    logger.info("---")
    
    # Run with AgentOS (production-ready, no reload)
    agent_os.serve(app=app, port=config.PORT, reload=False)
