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
agent, tracing_db, knowledge = asyncio.run(initialize_recipe_agent())

# Create AgentOS with the agent, knowledge base, and tracing enabled (if configured)
logger.info("Creating AgentOS instance...")
logger.info(f"Knowledge base: {knowledge is not None}")
logger.info(f"Tracing DB: {tracing_db is not None}")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    knowledge=[knowledge] if knowledge else [],
    tracing=config.ENABLE_TRACING,
    tracing_db=tracing_db,
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
    logger.info("🚀 Using Agno OS Platform (Recommended):")
    logger.info("   1. Signup: https://os.agno.com (free tier available)")
    logger.info("   2. Create or join a team")
    logger.info("   3. Add Local OS: Team dropdown → 'Add new OS' → 'Local'")
    logger.info(f"   4. Enter endpoint: http://localhost:{config.PORT}")
    logger.info("   5. Chat in platform UI with automatic schema-aware forms")
    logger.info("   6. View execution traces and performance metrics")
    logger.info("---")
    
    # Run with AgentOS (production-ready, no reload)
    agent_os.serve(app=app, port=config.PORT, reload=False)
