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
from src.models.models import ChatMessage, RecipeResponse, IngredientDetectionOutput
from src.mcp_tools.ingredients import detect_ingredients_tool
from src.mcp_tools.spoonacular import SpoonacularMCP
from src.prompts.prompts import get_system_instructions
from src.hooks.hooks import get_pre_hooks


@tool
async def detect_image_ingredients(image_data: str) -> IngredientDetectionOutput:
    """Extract ingredients from an uploaded image using Gemini vision API.
    
    This tool analyzes food images to detect and extract ingredient information
    with confidence scores. It supports both URL-based and Base64-encoded images.
    
    **When to Use:**
    - User uploads an image for ingredient detection
    - Need structured ingredient data with confidence scores
    - Want the agent to validate or ask clarifying questions about detected items
    
    **Image Format & Size:**
    - Supports: JPEG and PNG only
    - Maximum size: Configured by MAX_IMAGE_SIZE_MB (default: 5MB)
    
    **Processing Steps:**
    1. Retrieves image bytes from URL or decodes Base64
    2. Validates format (JPEG/PNG) and size constraints
    3. Calls Gemini vision API to extract ingredients
    4. Filters results by MIN_INGREDIENT_CONFIDENCE threshold
    5. Returns structured ingredient data with confidence scores
    
    Args:
        image_data: Either a URL string or Base64-encoded image.
            Examples:
            - "https://example.com/food.jpg" (URL)
            - "iVBORw0KGgoAAAANSUhEUg..." (Base64)
    
    Returns:
        IngredientDetectionOutput containing:
        - ingredients: List of detected ingredient names (filtered by confidence)
        - confidence_scores: Mapping of each ingredient to confidence (0.0-1.0)
        - image_description: Human-readable summary of detected items
        
        Example:
        {
            "ingredients": ["tomato", "basil", "mozzarella"],
            "confidence_scores": {"tomato": 0.95, "basil": 0.88, "mozzarella": 0.82},
            "image_description": "Detected ingredients: tomato (95%), basil (88%), mozzarella (82%)"
        }
    
    Raises:
        ValueError: If image cannot be processed, with details about the failure:
            - "Invalid image format. Only JPEG and PNG are supported."
            - "Image too large. Maximum size is 5MB"
            - "Failed to extract ingredients from image. Please try another image."
            - "No ingredients detected with sufficient confidence. Please try another image."
    """
    return await detect_ingredients_tool(image_data)


def initialize_recipe_agent(use_db: bool = True) -> Agent:
    """Factory function to initialize and configure the recipe recommendation agent (sync).
    
    This function:
    1. Initializes Spoonacular MCP with connection validation and fail-fast pattern
    2. Configures database (SQLite for development, PostgreSQL optional for production)
    3. Builds tools list based on IMAGE_DETECTION_MODE configuration
    4. Registers ingredient detection tool (tool mode only)
    5. Registers pre-hooks including ingredient extraction and guardrails
    6. Configures Agno Agent with system instructions and memory settings
    
    Args:
        use_db: If True, use persistent database. If False, run stateless without persistence.
    
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
    if use_db:
        if config.DATABASE_URL:
            logger.info(f"Using PostgreSQL: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else '...'}")
            db = PostgresDb(db_url=config.DATABASE_URL)
        else:
            logger.info("Using SQLite database: agno.db")
            db = SqliteDb(db_file="agno.db")
        logger.info("✓ Database configured")
    else:
        logger.info("Database persistence disabled (stateless mode)")
        db = None
        logger.info("✓ Stateless mode configured")
    
    # 3. Build tools list based on configuration
    logger.info("Step 3/5: Registering tools...")
    tools = [mcp_tools]  # Spoonacular MCP always included
    
    # Add ingredient detection tool if in tool mode
    if config.IMAGE_DETECTION_MODE == "tool":
        logger.info("Registering ingredient detection as tool (tool mode)")
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
