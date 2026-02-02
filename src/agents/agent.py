"""Agent initialization factory for Recipe Recommendation Service.

Factory function that initializes and configures the Agno Agent
with all orchestration settings, tools, pre-hooks, and system instructions.
"""

import os
import warnings
from agno.agent import Agent
from agno.models.google import Gemini
from agno.memory import MemoryManager
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearnedKnowledgeConfig, LearningMode
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


async def _initialize_mcp_tools():
    """Initialize MCP tools (Spoonacular) with connection validation (fail-fast pattern).

    Returns:
        MCPTools instance if enabled and successful, None otherwise.

    Raises:
        SystemExit: If MCP is enabled but initialization fails (fail-fast).
    """
    logger.info("Step 1/7: Checking MCP tools configuration...")

    if not config.USE_SPOONACULAR:
        logger.info("Spoonacular MCP disabled - using internal LLM knowledge mode")
        logger.info("✓ Internal knowledge mode configured")
        return None

    logger.info("Spoonacular MCP enabled - initializing...")
    spoonacular_mcp = SpoonacularMCP(
        api_key=config.SPOONACULAR_API_KEY,
        max_retries=config.MAX_RETRIES,
        retry_delays=[1, 2, 4],
        include_tools=["find_recipes_by_ingredients", "get_recipe_information"],
    )

    try:
        mcp_tools = await spoonacular_mcp.initialize()
        logger.info(
            "✓ Spoonacular MCP initialized successfully (filtered to: find_recipes_by_ingredients, get_recipe_information)"
        )
        return mcp_tools
    except Exception as e:
        logger.error(f"✗ MCP initialization failed: {e}")
        raise SystemExit(1) from e


def _register_tools(mcp_tools):
    """Build tools list based on configuration and IMAGE_DETECTION_MODE.

    Args:
        mcp_tools: MCP tools instance or None.

    Returns:
        List of registered tools.
    """
    logger.info("Step 2/7: Registering tools...")
    tools = []

    if mcp_tools:
        tools.append(mcp_tools)
        logger.info("✓ MCP tools registered")

    if config.IMAGE_DETECTION_MODE == "tool":
        logger.info("Registering ingredient detection as tool (tool mode)")
        tools.append(detect_image_ingredients)
        logger.info("✓ Ingredient detection tool registered")
    else:
        logger.info("Using ingredient detection in pre-hook mode (default)")

    logger.info(f"✓ {len(tools)} tool(s) registered")
    return tools


async def _initialize_tracing_db():
    """Initialize tracing with dedicated database for observability.

    Returns:
        Tracing database instance if successful, None otherwise.
    """
    logger.info("Step 3/7: Initializing tracing...")
    tracing_db = await initialize_tracing()
    if tracing_db:
        logger.info("✓ Tracing initialized with dedicated database")
    else:
        logger.info("✓ Tracing disabled or not available")
    return tracing_db


def _configure_database(use_db: bool):
    """Configure database for session persistence (SQLite or PostgreSQL).

    Args:
        use_db: If True, configure persistent database. If False, return None (stateless mode).

    Returns:
        Database instance (SqliteDb or PostgresDb) or None for stateless mode.
    """
    logger.info("Step 4/7: Configuring database for session persistence...")

    if not use_db:
        logger.info("Database persistence disabled (stateless mode)")
        logger.info("✓ Stateless mode configured")
        return None

    if config.DATABASE_URL:
        logger.info(f"Using PostgreSQL: {config.DATABASE_URL.split('@')[1] if '@' in config.DATABASE_URL else '...'}")
        db = PostgresDb(db_url=config.DATABASE_URL, id="recipe_agent_db")
    else:
        logger.info("Using SQLite database: tmp/recipe_agent_sessions.db")
        db = SqliteDb(db_file="tmp/recipe_agent_sessions.db", id="recipe_agent_db")

    logger.info("✓ Database configured")
    return db


async def _initialize_managers(db, knowledge):
    """Initialize memory manager, compression manager, and learning machine with cost-optimized models.

    Args:
        db: Database instance for persisting manager state.
        knowledge: Knowledge base instance for learning.

    Returns:
        Tuple of (memory_manager, compression_manager, learning_machine).
    """
    logger.info("Step 5a/7: Initializing memory manager with cost-optimized model...")
    memory_manager = MemoryManager(
        db=db,
        model=Gemini(
            id=config.MEMORY_MODEL,
            api_key=config.GEMINI_API_KEY,
        ),
        additional_instructions="Focus on extracting user preferences, dietary restrictions, and cuisine preferences for recipe recommendations. Keep memories concise and relevant to cooking/recipe context.",
    )
    logger.info("✓ Memory manager initialized with gemini-2.5-flash-lite for cost optimization")

    logger.info("Step 5b/7: Initializing compression manager with cost-optimized model...")
    compression_manager = CompressionManager(
        model=Gemini(
            id=config.MEMORY_MODEL,
            api_key=config.GEMINI_API_KEY,
        ),
        compress_tool_results_limit=config.TOOL_CALL_LIMIT,
        compress_tool_call_instructions="Summarize tool results focusing on key facts, ingredients, recipes, and cooking information. Remove redundant details while preserving essential recipe data.",
    )
    logger.info("✓ Compression manager initialized with cost-optimized model")

    logger.info("Step 5c/7: Initializing learning machine for agent learning...")
    learning_machine = None
    if config.ENABLE_LEARNING:
        # Parse learning mode from string (ALWAYS, AGENTIC, PROPOSE)
        mode_map = {
            "ALWAYS": LearningMode.ALWAYS,
            "AGENTIC": LearningMode.AGENTIC,
            "PROPOSE": LearningMode.PROPOSE,
        }
        learning_mode = mode_map.get(config.LEARNING_MODE.upper(), LearningMode.AGENTIC)
        
        learning_machine = LearningMachine(
            db=db,
            model=Gemini(
                id=config.MEMORY_MODEL,
                api_key=config.GEMINI_API_KEY,
            ),
            # LearnedKnowledge: Agent learns recipe insights and preferences dynamically
            # AGENTIC mode: Agent decides when to save learnings (recommended for recipes)
            # Namespace="global": Learnings benefit all users (shared recipe insights)
            learned_knowledge=LearnedKnowledgeConfig(
                mode=learning_mode,
                namespace="global",  # Shared recipe learnings across all users
            ),
        )
        logger.info(f"✓ Learning machine initialized with {config.LEARNING_MODE} mode (global namespace for shared recipe insights)")
    else:
        logger.info("✓ Learning machine disabled (ENABLE_LEARNING=false)")

    return memory_manager, compression_manager, learning_machine


def _register_hooks(knowledge):
    """Register pre-hooks and post-hooks for request/response processing.

    Args:
        knowledge: Knowledge base instance for post-hooks.

    Returns:
        Tuple of (pre_hooks, post_hooks).
    """
    logger.info("Step 6a/7: Registering pre-hooks and guardrails...")
    pre_hooks = get_pre_hooks()
    logger.info(f"✓ {len(pre_hooks)} pre-hooks registered")

    logger.info("Step 6b/7: Registering post-hooks...")
    post_hooks = get_post_hooks(knowledge_base=knowledge)
    logger.info(
        f"✓ {len(post_hooks)} post-hooks registered: {[h.__name__ if hasattr(h, '__name__') else str(h) for h in post_hooks]}"
    )

    return pre_hooks, post_hooks


def _create_agent(db, knowledge, memory_manager, compression_manager, learning_machine, tools, pre_hooks, post_hooks) -> Agent:
    """Create and configure the Agno Agent instance.

    Args:
        db: Database instance for session persistence.
        knowledge: Knowledge base instance for learnings.
        memory_manager: Memory manager for user preferences.
        compression_manager: Compression manager for tool results.
        learning_machine: Learning machine for dynamic insight extraction (optional).
        tools: List of registered tools.
        pre_hooks: List of pre-hooks for request processing.
        post_hooks: List of post-hooks for response processing.

    Returns:
        Configured Agent instance.
    """
    logger.info("Step 7/7: Configuring Agno Agent...")

    agent = Agent(
        # === Model Configuration ===
        model=Gemini(
            id=config.GEMINI_MODEL,
            api_key=config.GEMINI_API_KEY,
            temperature=config.TEMPERATURE,  # 0.2 = consistency with some creativity
            max_output_tokens=config.MAX_OUTPUT_TOKENS,  # 8192 supports full response with multiple recipes and instructions (Gemini supports up to 65,536)
            thinking_level=config.THINKING_LEVEL,  # Extended reasoning depth control
        ),
        # === Storage & Knowledge ===
        db=db,  # SQLite (dev) or PostgreSQL (prod) for session persistence
        knowledge=knowledge,  # LanceDB vector store for learnings/troubleshooting (NOTE: disabled by default - use LearnedKnowledge instead for dynamic learning)
        search_knowledge=config.SEARCH_KNOWLEDGE,  # LLM-accessible knowledge search (disabled by default - Knowledge vs LearnedKnowledge: use one, not both)
        learning=learning_machine,  # Learning Machine: dynamic insight extraction and preferences (AGENTIC mode by default)
        memory_manager=memory_manager,  # Cost-optimized memory operations with smaller model
        compression_manager=compression_manager,  # Cost-optimized tool result compression
        # === Tools & Hooks ===
        tools=tools,  # MCP + optional ingredient detection tool
        pre_hooks=pre_hooks,  # Ingredient extraction + safety guardrails
        post_hooks=post_hooks,  # Response field extraction for UI rendering
        # === Input/Output Schemas ===
        input_schema=ChatMessage,  # Validates incoming messages
        output_schema=RecipeResponse,  # Structures recipe response with metadata
        structured_outputs=True,  # Force native structured outputs (Gemini supports this - guarantees schema-valid JSON at API level)
        # === Instructions & State ===
        instructions=get_system_instructions(
            max_recipes=config.MAX_RECIPES,
            max_tool_calls=config.TOOL_CALL_LIMIT,
            use_spoonacular=config.USE_SPOONACULAR,
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
        search_session_history=config.SEARCH_SESSION_HISTORY,  # Search across multiple past sessions
        num_history_sessions=config.NUM_HISTORY_SESSIONS,  # Include last 2 sessions in history search (performance tip: keep low)
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
    return agent


async def initialize_recipe_agent(use_db: bool = True) -> Agent:
    """Factory function to initialize and configure the recipe recommendation agent (async).

    Orchestrates initialization of all components in sequence:
    1. Spoonacular MCP with fail-fast validation
    2. Tracing database for observability
    3. Session persistence database (SQLite or PostgreSQL)
    4. Knowledge base for learnings and troubleshooting
    5. Memory, compression, and learning managers (cost-optimized)
    6. Tool registration (MCP + ingredient detection)
    7. Pre-hooks and post-hooks registration
    8. Agent configuration with system instructions

    Args:
        use_db: If True, use persistent database. If False, run stateless without persistence.

    Returns:
        Tuple of (Agent, tracing_db, knowledge_base).

    Raises:
        SystemExit: If MCP initialization fails (fail-fast pattern).
    """
    logger.info("=== Initializing Recipe Recommendation Agent ===")

    # Initialize components in sequence
    mcp_tools = await _initialize_mcp_tools()
    tools = _register_tools(mcp_tools)
    tracing_db = await _initialize_tracing_db()
    db = _configure_database(use_db)
    knowledge = await initialize_knowledge_base(db=db)
    memory_manager, compression_manager, learning_machine = await _initialize_managers(db, knowledge)
    pre_hooks, post_hooks = _register_hooks(knowledge)
    agent = _create_agent(db, knowledge, memory_manager, compression_manager, learning_machine, tools, pre_hooks, post_hooks)

    logger.info("=== Agent initialization complete ===")
    return agent, tracing_db, knowledge
