"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory
- Creates AgentOS instance with agent
- Serves REST API and Web UI automatically

Run with: python app.py
"""

from agno.os import AgentOS

from config import config
from logger import logger
from agent import initialize_recipe_agent


# Initialize agent using factory pattern
logger.info("Starting Recipe Recommendation Service initialization...")
agent = initialize_recipe_agent()

# Create AgentOS with the agent
logger.info("Creating AgentOS instance...")
agent_os = AgentOS(
    description="Recipe Recommendation Service",
    agents=[agent],
)

# Get the FastAPI app
app = agent_os.get_app()


if __name__ == "__main__":
    logger.info(f"Starting Recipe Recommendation Service on port {config.PORT}")
    logger.info(f"Image detection mode: {config.IMAGE_DETECTION_MODE}")
    logger.info(f"Access Web UI at: http://localhost:{config.PORT}")
    logger.info(f"API docs available at: http://localhost:{config.PORT}/docs")
    logger.info("---")
    
    # Run with AgentOS
    agent_os.serve(app="app:app", reload=True)
