"""Agent initialization factory for Recipe Recommendation Service.

Factory function that initializes and configures the Agno Agent
with all orchestration settings, tools, pre-hooks, and system instructions.
"""

import asyncio

from agno.agent import Agent
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from agno.tools import tool

from src.utils.config import config
from src.utils.logger import logger
from src.models.models import RecipeRequest, RecipeResponse
from src.mcp_tools.ingredients import detect_ingredients_tool
from src.mcp_tools.spoonacular import SpoonacularMCP
from src.prompts.prompts import get_system_instructions
from src.hooks.hooks import get_pre_hooks


def initialize_recipe_agent() -> Agent:
    """Factory function to initialize and configure the recipe recommendation agent (sync).
    
    This function:
    1. Initializes Spoonacular MCP with connection validation and fail-fast pattern
    2. Configures database (SQLite for development, PostgreSQL optional for production)
    3. Builds tools list based on IMAGE_DETECTION_MODE configuration
    4. Registers ingredient detection tool (tool mode only)
    5. Registers pre-hooks including ingredient extraction and guardrails
    6. Configures Agno Agent with system instructions and memory settings
    
    Returns:
        Agent: Fully configured recipe recommendation agent ready for use with AgentOS.
        
    Raises:
        SystemExit: If MCP initialization fails (fail-fast pattern).
    """
    logger.info("=== Initializing Recipe Recommendation Agent ===")
    
    # 1. Initialize MCP FIRST (fail-fast if unreachable)
    logger.info("Step 1/5: Initializing Spoonacular MCP...")
    spoonacular_mcp = SpoonacularMCP(
        api_key=config.SPOONACULAR_API_KEY,
        max_retries=3,
        retry_delays=[1, 2, 4],
    )
    try:
        # Run async initialization synchronously using asyncio.run
        mcp_tools = asyncio.run(spoonacular_mcp.initialize())
        logger.info("✓ Spoonacular MCP initialized successfully")
    except Exception as e:
        logger.error(f"✗ MCP initialization failed: {e}")
        raise SystemExit(1)
    
    # 2. Configure database for session persistence
    logger.info("Step 2/5: Configuring database for session persistence...")
    if config.DATABASE_URL:
        logger.info(f"Using PostgreSQL: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else '...'}")
        db = PostgresDb(db_url=config.DATABASE_URL)
    else:
        logger.info("Using SQLite database: agno.db")
        db = SqliteDb(db_file="agno.db")
    logger.info("✓ Database configured")
    
    # 3. Build tools list based on configuration
    logger.info("Step 3/5: Registering tools...")
    tools = [mcp_tools]  # Spoonacular MCP always included
    
    # Add ingredient detection tool if in tool mode
    if config.IMAGE_DETECTION_MODE == "tool":
        logger.info("Registering ingredient detection as tool (tool mode)")
        
        @tool
        def detect_image_ingredients(image_data: str) -> dict:
            """Extract ingredients from an uploaded image using Gemini vision API.
            
            Call this tool when a user uploads an image to detect ingredients.
            The tool returns detected ingredients with confidence scores.
            
            Args:
                image_data: Base64-encoded image string or image URL.
                
            Returns:
                Dict with 'ingredients' list, 'confidence_scores' dict, and 'image_description'.
                
            Raises:
                ValueError: If image cannot be processed.
            """
            return detect_ingredients_tool(image_data)
        
        tools.append(detect_image_ingredients)
        logger.info("✓ Ingredient detection tool registered")
    else:
        logger.info("Using ingredient detection in pre-hook mode (default)")
    
    logger.info(f"✓ {len(tools)} tools registered")
    
    # 4. Get pre-hooks (includes ingredient extraction and guardrails)
    logger.info("Step 4/5: Registering pre-hooks and guardrails...")
    pre_hooks = get_pre_hooks()
    logger.info(f"✓ {len(pre_hooks)} pre-hooks registered")
    
    # 5. Configure Agno Agent
    logger.info("Step 5/5: Configuring Agno Agent...")
    # Generate system instructions with config values
    system_instructions = get_system_instructions(
        max_recipes=config.MAX_RECIPES,
        max_history=config.MAX_HISTORY,
        min_ingredient_confidence=config.MIN_INGREDIENT_CONFIDENCE,
    )
    agent = Agent(
        model=Gemini(
            id=config.GEMINI_MODEL,
            api_key=config.GEMINI_API_KEY,
        ),
        db=db,
        tools=tools,
        pre_hooks=pre_hooks,
        input_schema=RecipeRequest,
        output_schema=RecipeResponse,
        instructions=system_instructions,
        # Memory settings
        add_history_to_context=True,
        num_history_runs=config.MAX_HISTORY,
        enable_user_memories=True,
        enable_session_summaries=True,
        compress_tool_results=True,
        # Agent metadata
        name="Recipe Recommendation Agent",
        description="Transforms ingredient images into recipe recommendations with conversational memory",
    )
    logger.info("✓ Agent configured successfully")
    logger.info("=== Agent initialization complete ===")
    
    return agent
