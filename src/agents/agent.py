"""Agent initialization factory for Recipe Recommendation Service.

Factory function that initializes and configures the Agno Agent
with all orchestration settings, tools, pre-hooks, and system instructions.
"""

import os
import asyncio
import warnings
from agno.agent import Agent
from agno.models.google import Gemini
from agno.memory import MemoryManager
from agno.compression.manager import CompressionManager
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.tools import tool

from src.utils.config import config
from src.utils.logger import logger
from src.utils.tracing import initialize_tracing
from src.models.models import ChatMessage, RecipeResponse, IngredientDetectionOutput
from src.mcp_tools.ingredients import detect_ingredients_tool
from src.mcp_tools.spoonacular import SpoonacularMCP
from src.prompts.prompts import get_system_instructions
from src.hooks.hooks import get_pre_hooks, get_post_hooks

# Suppress LanceDB fork-safety warning (not using multiprocessing)
warnings.filterwarnings("ignore", message="lance is not fork-safe")

async def initialize_knowledge_base(db=None) -> Knowledge:
    """Initialize knowledge base for recipe troubleshooting and learnings.
    
    Uses LanceDB for vector storage and SentenceTransformer embeddings (lightweight, no API calls).
    Stores troubleshooting findings and learnings for agent reference and improvement over time.
    
    Args:
        db: Optional database for persisting knowledge content metadata to SQLite (for AgentOS UI display).
           This enables knowledge to appear in the AgentOS platform's Knowledge tab.
    """
    logger.info("Initializing knowledge base...")
    try:
        os.makedirs("tmp/lancedb", exist_ok=True)
        knowledge = Knowledge(
            vector_db=LanceDb(
                uri="tmp/lancedb",
                table_name="recipe_agent_knowledge",
                embedder=SentenceTransformerEmbedder(),
            ),
            contents_db=db,  # Persist content metadata to SQLite for AgentOS UI
        )
        logger.info("✓ Knowledge base initialized")
        return knowledge
    except Exception as e:
        logger.warning(f"Knowledge base initialization failed: {e}. Continuing without knowledge base.")
        return None


@tool
# We use @tool decorator to register this function as an Agno tool, docstring used for tool description for the agent.
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


async def initialize_recipe_agent(use_db: bool = True) -> Agent:
    """Factory function to initialize and configure the recipe recommendation agent (async).
    
    This async function:
    1. Initializes Spoonacular MCP with connection validation and fail-fast pattern
    2. Initializes tracing with dedicated database for observability
    3. Configures database (SQLite for development, PostgreSQL optional for production)
    4. Builds tools list based on IMAGE_DETECTION_MODE configuration
    5. Registers ingredient detection tool (tool mode only)
    6. Registers pre-hooks including ingredient extraction and guardrails
    7. Configures Agno Agent with system instructions and memory settings
    
    Args:
        use_db: If True, use persistent database. If False, run stateless without persistence.
    
    Returns:
        Agent: Fully configured recipe recommendation agent ready for use with AgentOS.
        
    Raises:
        SystemExit: If MCP initialization fails (fail-fast pattern).
    """
    logger.info("=== Initializing Recipe Recommendation Agent ===")
    
    # 1. Initialize MCP (if enabled, with fail-fast if unreachable)
    logger.info("Step 1/7: Checking Spoonacular MCP configuration...")
    mcp_tools = None
    if config.USE_SPOONACULAR:
        logger.info("Spoonacular MCP enabled - initializing...")
        spoonacular_mcp = SpoonacularMCP(
            api_key=config.SPOONACULAR_API_KEY,
            max_retries= config.MAX_RETRIES,
            retry_delays=[1, 2, 4],
            include_tools=["find_recipes_by_ingredients", "get_recipe_information"],
        )
        try:
            mcp_tools = await spoonacular_mcp.initialize()
            logger.info("✓ Spoonacular MCP initialized successfully (filtered to: find_recipes_by_ingredients, get_recipe_information)")
        except Exception as e:
            logger.error(f"✗ MCP initialization failed: {e}")
            raise SystemExit(1)
    else:
        logger.info("Spoonacular MCP disabled - using internal LLM knowledge mode")
        logger.info("✓ Internal knowledge mode configured")
    
    # 2. Initialize tracing (if enabled)
    logger.info("Step 2/7: Initializing tracing...")
    tracing_db = await initialize_tracing()
    if tracing_db:
        logger.info("✓ Tracing initialized with dedicated database")
    else:
        logger.info("✓ Tracing disabled or not available")
    
    # 2b. Configure database for session persistence FIRST (needed for knowledge base)
    logger.info("Step 3/7: Configuring database for session persistence...")
    if use_db:
        if config.DATABASE_URL:
            logger.info(f"Using PostgreSQL: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else '...'}")
            db = PostgresDb(db_url=config.DATABASE_URL, id="recipe_agent_db")
        else:
            logger.info("Using SQLite database: tmp/recipe_agent_sessions.db")
            db = SqliteDb(db_file="tmp/recipe_agent_sessions.db", id="recipe_agent_db")
        logger.info("✓ Database configured")
    else:
        logger.info("Database persistence disabled (stateless mode)")
        db = None
        logger.info("✓ Stateless mode configured")
    
    # 2c. Initialize knowledge base AFTER db is ready (uses db for content persistence)
    logger.info("Step 2c/7: Initializing knowledge base...")
    knowledge = await initialize_knowledge_base(db=db)
    
    # 2d. Initialize memory manager with smaller model for cost optimization
    logger.info("Step 2d/7: Initializing memory manager with cost-optimized model...")
    memory_manager = MemoryManager(
        db=db,
        model=Gemini(
            id=config.MEMORY_MODEL,  # Configurable smaller model for memory operations (cost optimization)
            api_key=config.GEMINI_API_KEY,
        ),
        additional_instructions="Focus on extracting user preferences, dietary restrictions, and cuisine preferences for recipe recommendations. Keep memories concise and relevant to cooking/recipe context."
    )
    logger.info("✓ Memory manager initialized with gemini-2.5-flash-lite for cost optimization")
    
    # 2e. Initialize compression manager with smaller model for cost optimization
    logger.info("Step 2e/7: Initializing compression manager with cost-optimized model...")
    compression_manager = CompressionManager(
        model=Gemini(
            id=config.MEMORY_MODEL,  # Use same cost-optimized model for compression
            api_key=config.GEMINI_API_KEY,
        ),
        compress_tool_results_limit=config.TOOL_CALL_LIMIT,  # Compress after configured number of tool calls
        compress_tool_call_instructions="Summarize tool results focusing on key facts, ingredients, recipes, and cooking information. Remove redundant details while preserving essential recipe data."
    )
    logger.info("✓ Compression manager initialized with cost-optimized model")
    
    # 3. Build tools list based on configuration
    logger.info("Step 3/5: Registering tools...")
    tools = []
    
    # Add Spoonacular MCP tools if enabled
    if mcp_tools:
        tools.append(mcp_tools)
        logger.info("✓ Spoonacular MCP tools registered")
    
    # Add ingredient detection tool if in tool mode
    if config.IMAGE_DETECTION_MODE == "tool":
        logger.info("Registering ingredient detection as tool (tool mode)")
        tools.append(detect_image_ingredients)
        logger.info("✓ Ingredient detection tool registered")
    else:
        logger.info("Using ingredient detection in pre-hook mode (default)")
    
    logger.info(f"✓ {len(tools)} tool(s) registered")
    
    # 5. Get pre-hooks (includes ingredient extraction and guardrails)
    logger.info("Step 5/7: Registering pre-hooks and guardrails...")
    pre_hooks = get_pre_hooks()
    logger.info(f"✓ {len(pre_hooks)} pre-hooks registered")
    
    # 5b. Get post-hooks (includes response field extraction for UI rendering)
    logger.info("Step 5b/7: Registering post-hooks...")
    post_hooks = get_post_hooks(knowledge_base=knowledge)
    logger.info(f"✓ {len(post_hooks)} post-hooks registered: {[h.__name__ if hasattr(h, '__name__') else str(h) for h in post_hooks]}")
    
    # 6. Configure Agno Agent
    logger.info("Step 6/7: Configuring Agno Agent...")
    
    # Get static system instructions
    logger.info("System instructions configured")
    
    agent = Agent(
        # === Model Configuration ===
        model=Gemini(
            id=config.GEMINI_MODEL,
            api_key=config.GEMINI_API_KEY,
            temperature=config.TEMPERATURE,  # 0.2 = consistency with some creativity
            max_output_tokens=config.MAX_OUTPUT_TOKENS,  # 2048 supports full recipe with instructions
            thinking_level=config.THINKING_LEVEL,  # Extended reasoning depth control
        ),
        
        # === Storage & Knowledge ===
        db=db,  # SQLite (dev) or PostgreSQL (prod) for session persistence
        knowledge=knowledge,  # LanceDB vector store for learnings/troubleshooting
        search_knowledge=config.SEARCH_KNOWLEDGE,  # LLM-accessible knowledge search
        memory_manager=memory_manager,  # Cost-optimized memory operations with smaller model
        compression_manager=compression_manager,  # Cost-optimized tool result compression
        
        # === Tools & Hooks ===
        tools=tools,  # Spoonacular MCP + optional ingredient detection tool
        pre_hooks=pre_hooks,  # Ingredient extraction + safety guardrails
        post_hooks=post_hooks,  # Response field extraction for UI rendering
        
        # === Input/Output Schemas ===
        input_schema=ChatMessage,  # Validates incoming messages
        output_schema=RecipeResponse,  # Structures recipe response with metadata
        
        # === Instructions & State ===
        instructions=get_system_instructions(
            max_recipes=config.MAX_RECIPES,
            max_tool_calls=config.TOOL_CALL_LIMIT,
            use_spoonacular=config.USE_SPOONACULAR
        ),
        
        # === Retry & Error Handling ===
        retries=config.MAX_RETRIES,  # 3 retry attempts for transient failures
        exponential_backoff=config.EXPONENTIAL_BACKOFF,  # 2s → 4s → 8s delays (handles rate limits)
        delay_between_retries=config.DELAY_BETWEEN_RETRIES,  # Initial backoff delay in seconds
        
        # === Memory & Context ===
        add_history_to_context=config.ADD_HISTORY_TO_CONTEXT,  # Include conversation history (local database operation)
        read_tool_call_history=config.READ_TOOL_CALL_HISTORY,  # LLM can access previous tool calls (local operation)
        update_knowledge=config.UPDATE_KNOWLEDGE,  # LLM can add learnings to KB (local vector database operation)
        read_chat_history=config.READ_CHAT_HISTORY,  # Dedicated tool for history access (local operation)
        num_history_runs=config.MAX_HISTORY,  # 3 turns of conversation context
        enable_user_memories=config.ENABLE_USER_MEMORIES,  # Track user preferences (requires extra LLM API calls)
        enable_session_summaries=config.ENABLE_SESSION_SUMMARIES,  # Auto-compress context (requires extra LLM API calls)
        compress_tool_results=config.COMPRESS_TOOL_RESULTS,  # Reduce tool output verbosity
        max_tool_calls_from_history=config.TOOL_CALL_LIMIT - 1,  # Full tool call history access
        
        # === Execution Limits ===
        tool_call_limit=config.TOOL_CALL_LIMIT,  # Max tool calls per session
        reasoning_max_steps=config.TOOL_CALL_LIMIT,  # Complements tool_call_limit for reasoning depth
        
        # === Metadata ===
        name="Recipe Recommendation Agent",
        description="Transforms ingredient images into recipe recommendations with conversational memory",
    )
    logger.info(f"✓ Agent configured successfully with maximum {config.TOOL_CALL_LIMIT} tool calls per request")
    logger.info("=== Agent initialization complete ===")
    
    return agent, tracing_db, knowledge
