"""AgentOS Application - Recipe Recommendation Service.

Single entry point for the complete recipe recommendation system:
- Initializes agent from agent.py factory (async)
- Creates AgentOS instance with agent
- Serves REST API and Web UI automatically via AgentOS

Run with: python app.py

Features:
- Web UI: ChatGPT-like interface at http://localhost:PORT
- AGUI endpoints: POST /agui for agent interaction
- OpenAPI docs: http://localhost:PORT/docs
- Session management: Automatic per session_id
- Tool lifecycle: MCPs initialized before AgentOS starts
"""

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


# Initialize agent using factory pattern
logger.info("Starting Recipe Recommendation Service initialization...")
agent = initialize_recipe_agent()

# Create AgentOS with the agent and Web UI interface
logger.info("Creating AgentOS instance with Web UI...")
agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)

# Get the FastAPI app for external serving (e.g., Docker)
app = agent_os.get_app()

# Override root path to serve web UI instead of API info
# Remove the default "/" route from AgentOS
ui_dir = Path(__file__).parent / "src" / "ui"
if ui_dir.exists():
    # Remove existing root route by filtering router.routes
    root_routes_to_remove = [route for route in app.router.routes if hasattr(route, 'path') and route.path == '/']
    for route in root_routes_to_remove:
        app.router.routes.remove(route)
    
    # Add HTML UI at root
    @app.get("/")
    async def serve_ui():
        """Serve the web UI at the root path."""
        return FileResponse(ui_dir / "index.html")
    
    # Mount static assets
    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")


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
    # Pass the app object directly instead of string to avoid reimport
    agent_os.serve(app=app, port=config.PORT, reload=False)
