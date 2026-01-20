"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory
- Creates AgentOS instance for REST API
- Serves recipe recommendation endpoints

Run with: python app.py
"""

from agno.os import AgentOS

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


# Initialize agent using factory pattern
logger.info("Starting Recipe Recommendation Service initialization...")
agent = initialize_recipe_agent()

# Create AgentOS with the agent (no UI, API only)
logger.info("Creating AgentOS instance...")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
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
