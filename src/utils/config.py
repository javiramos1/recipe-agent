"""Configuration management for Recipe Service.

Loads environment variables from system environment and .env file.
Priority order: system environment > .env file > hardcoded defaults
"""

import os
from typing import Optional

from dotenv import load_dotenv


# Load .env file (if exists, silently continues if missing)
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables."""
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        # Spoonacular Configuration: Enable/disable external recipe API
        self.USE_SPOONACULAR: bool = os.getenv("USE_SPOONACULAR", "true").lower() in ("true", "1", "yes")
        # Spoonacular API Key: required if USE_SPOONACULAR is true
        self.SPOONACULAR_API_KEY: str = os.getenv("SPOONACULAR_API_KEY", "")
        # Default: gemini-3-flash-preview (fast, cost-effective)
        # For best results: use gemini-3-pro-preview for complex recipe reasoning
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        # Image Detection Model: separate model optimized for vision tasks
        # Default: gemini-2.5-flash-lite (fast, cost-effective for images)
        # For better accuracy: use gemini-3-pro-preview for complex image analysis
        self.IMAGE_DETECTION_MODEL: str = os.getenv("IMAGE_DETECTION_MODEL", "gemini-2.5-flash-lite")
        # Memory Model: separate model for memory operations and tool compression
        # Default: gemini-2.5-flash-lite (cost-optimized for background operations)
        # Used for: user memories, session summaries, and tool result compression
        # Can be different from main model to reduce costs for background operations
        self.MEMORY_MODEL: str = os.getenv("MEMORY_MODEL", "gemini-2.5-flash-lite")
        # Server Port
        self.PORT: int = int(os.getenv("PORT", "7777"))
        # Maximum number of previous interactions to include in context. Default: 3
        self.MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "3"))
        # Maximum number of recipe recommendations to return. Default: 10
        self.MAX_RECIPES: int = int(os.getenv("MAX_RECIPES", "10"))
        # Maximum image size (in MB) that can be processed. Default: 5 MB
        self.MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
        # Minimum confidence score (0.0 - 1.0) for ingredient detection. Default: 0.7
        self.MIN_INGREDIENT_CONFIDENCE: float = float(os.getenv("MIN_INGREDIENT_CONFIDENCE", "0.7"))
        # Image Detection Mode: "pre-hook" or "tool"
        # "pre-hook": process images before main LLM call (faster, lower cost)
        # "tool": provide image analysis as tool for LLM to call (more flexible, higher cost)
        self.IMAGE_DETECTION_MODE: str = os.getenv("IMAGE_DETECTION_MODE", "pre-hook")
        # Image Compression: Enable/disable image compression before processing
        self.COMPRESS_IMG: bool = os.getenv("COMPRESS_IMG", "true").lower() in ("true", "1", "yes")
        # Image Compression Threshold: Only compress if image size is below this (in KB)
        # Default: 300 KB - images above this size are already compressed enough
        self.COMPRESS_IMG_THRESHOLD_KB: int = int(os.getenv("COMPRESS_IMG_THRESHOLD_KB", "300"))
        # Output Format: "json" or "markdown". Default: "json"
        # "json": structured output for programmatic consumption
        # "markdown": human-readable format for direct display
        self.OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "json")
        # Database URL: Optional database connection string for persistent storage for production use
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        # Tracing Configuration. 
        # ENABLE_TRACING: Enable/disable tracing of agent interactions
        self.ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "true").lower() in ("true", "1", "yes")
        # TRACING_DB_TYPE: Type of database for tracing ("sqlite" or "postgres")
        self.TRACING_DB_TYPE: str = os.getenv("TRACING_DB_TYPE", "sqlite")
        # TRACING_DB_FILE: SQLite database file name for tracing (if using sqlite)
        self.TRACING_DB_FILE: str = os.getenv("TRACING_DB_FILE", "agno_traces.db")
        # Tool Call Limit: Maximum number of tool calls agent can make per request
        self.TOOL_CALL_LIMIT: int = int(os.getenv("TOOL_CALL_LIMIT", "12"))
        # LLM Model Parameters
        # Temperature: Controls randomness (0.0 = deterministic, 1.0 = max randomness)
        # For recipes: 0.2 balances creativity with consistency
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))
        # Max Output Tokens: Maximum length of model response
        # For recipes: 2048 is sufficient for full recipe with instructions
        self.MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
        # Thinking Level: Enables extended thinking for complex reasoning
        # Options: "low", "high" - Recipe recommendations benefit from low/high thinking
        # "low" = fastest (no extended thinking), "high" = slowest but most thorough
        # Default: None (thinking disabled) This has been proved to work best in testing when using external tools
        self.THINKING_LEVEL: str = os.getenv("THINKING_LEVEL", None)
        
        # Agent Retry Configuration - handles transient API failures gracefully
        # MAX_RETRIES: Number of retry attempts for failed API calls (exponential backoff)
        self.MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
        # DELAY_BETWEEN_RETRIES: Initial delay in seconds (doubled each retry if exponential_backoff=True)
        self.DELAY_BETWEEN_RETRIES: int = int(os.getenv("DELAY_BETWEEN_RETRIES", "2"))
        # EXPONENTIAL_BACKOFF: Enable exponential backoff for rate limit handling
        self.EXPONENTIAL_BACKOFF: bool = os.getenv("EXPONENTIAL_BACKOFF", "true").lower() in ("true", "1", "yes")
        
        # Agent Memory & History Settings - control context enrichment and knowledge management
        # ====================================================================================
        # MEMORY STRATEGY: Option 1 - Automatic Context (Recommended for most use cases)
        # - Automatic recent history inclusion for conversational continuity
        # - No redundant on-demand history tools to avoid token bloat
        # - Balances performance with conversational awareness
        #
        # Alternative: Option 2 - Selective Access (For complex workflows needing deep history)
        # - Agent decides when to access history via dedicated tools
        # - Better for analytics/auditing or when context management is critical
        #
        # Alternative: Option 3 - Hybrid (Advanced users with specific needs)
        # - Both automatic and on-demand access
        # - Use max_tool_calls_from_history to control context size

        # ADD_HISTORY_TO_CONTEXT: Include recent conversation history in LLM context automatically
        # Benefits: Seamless conversational continuity, remembers recent preferences/discussions
        # Trade-offs: Increases token usage, may include irrelevant history
        # Cost: Local database operation (no extra LLM API calls)
        # Recommended: True for conversational agents, False for single-turn or context-sensitive apps
        self.ADD_HISTORY_TO_CONTEXT: bool = os.getenv("ADD_HISTORY_TO_CONTEXT", "true").lower() in ("true", "1", "yes")

        # READ_TOOL_CALL_HISTORY: Provide get_tool_call_history() tool for agent to access previous tool calls
        # Benefits: Agent can analyze tool usage patterns, reference past tool results
        # Trade-offs: Redundant if add_history_to_context=True (tool calls already in context)
        # Cost: Local database operation (no extra LLM API calls)
        # Recommended: False when add_history_to_context=True to avoid redundancy and token bloat
        self.READ_TOOL_CALL_HISTORY: bool = os.getenv("READ_TOOL_CALL_HISTORY", "false").lower() in ("true", "1", "yes")

        # UPDATE_KNOWLEDGE: Allow LLM to add learnings and troubleshooting to knowledge base
        # Benefits: Agent learns from experience, improves over time, shares insights across sessions
        # Trade-offs: Requires knowledge base setup, may add irrelevant information
        # Cost: Local vector database operation (no extra LLM API calls)
        # Recommended: True for learning agents, False for stateless or privacy-sensitive applications
        self.UPDATE_KNOWLEDGE: bool = os.getenv("UPDATE_KNOWLEDGE", "true").lower() in ("true", "1", "yes")

        # READ_CHAT_HISTORY: Provide get_chat_history() tool for agent to search entire chat history
        # Benefits: Agent can reference any past message when needed, deep historical analysis
        # Trade-offs: Redundant if add_history_to_context=True (recent history already included)
        # Cost: Local database operation (no extra LLM API calls)
        # Recommended: False when add_history_to_context=True to avoid redundancy and token bloat
        self.READ_CHAT_HISTORY: bool = os.getenv("READ_CHAT_HISTORY", "false").lower() in ("true", "1", "yes")

        # ENABLE_USER_MEMORIES: Store and track user preferences across sessions
        # Benefits: Personalized experience, remembers dietary restrictions, cuisine preferences
        # Trade-offs: Privacy considerations, requires database storage
        # Cost: Requires extra LLM API calls for preference extraction and storage
        # Recommended: True for personalized agents, False for anonymous or single-session use
        self.ENABLE_USER_MEMORIES: bool = os.getenv("ENABLE_USER_MEMORIES", "true").lower() in ("true", "1", "yes")

        # ENABLE_SESSION_SUMMARIES: Auto-generate and store session summaries for context compression
        # Benefits: Long-term memory without full context bloat, efficient storage
        # Trade-offs: Summary quality depends on LLM, may lose nuance
        # Cost: Requires extra LLM API calls for automatic summary generation
        # Recommended: False for cost optimization (default), True for long conversations needing compression
        self.ENABLE_SESSION_SUMMARIES: bool = os.getenv("ENABLE_SESSION_SUMMARIES", "false").lower() in ("true", "1", "yes")

        # COMPRESS_TOOL_RESULTS: Compress/reduce verbosity of tool outputs in context
        # Benefits: Reduces token usage, focuses on essential information
        # Trade-offs: May lose some detail, compression quality varies
        # Recommended: True for token efficiency, False when full tool output details are needed
        self.COMPRESS_TOOL_RESULTS: bool = os.getenv("COMPRESS_TOOL_RESULTS", "true").lower() in ("true", "1", "yes")

        # SEARCH_KNOWLEDGE: Allow agent to search knowledge base during reasoning
        # Benefits: Access to learned patterns, troubleshooting history, shared insights
        # Trade-offs: Requires knowledge base setup, may introduce irrelevant information
        # Recommended: True when knowledge base is available, False for simple stateless agents
        self.SEARCH_KNOWLEDGE: bool = os.getenv("SEARCH_KNOWLEDGE", "true").lower() in ("true", "1", "yes")

    def validate(self) -> None:
        """Validate required configuration.

        Raises:
            ValueError: If required API keys are missing or invalid values provided.
        """
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        # Only validate Spoonacular key if Spoonacular mode is enabled
        if self.USE_SPOONACULAR and not self.SPOONACULAR_API_KEY:
            raise ValueError("SPOONACULAR_API_KEY environment variable is required when USE_SPOONACULAR=true")
        if self.IMAGE_DETECTION_MODE not in ("pre-hook", "tool"):
            raise ValueError(
                f"IMAGE_DETECTION_MODE must be 'pre-hook' or 'tool', got: {self.IMAGE_DETECTION_MODE}"
            )
        if self.OUTPUT_FORMAT not in ("json", "markdown"):
            raise ValueError(
                f"OUTPUT_FORMAT must be 'json' or 'markdown', got: {self.OUTPUT_FORMAT}"
            )
        if self.TRACING_DB_TYPE not in ("sqlite", "postgres"):
            raise ValueError(
                f"TRACING_DB_TYPE must be 'sqlite' or 'postgres', got: {self.TRACING_DB_TYPE}"
            )
        if not (0.0 <= self.TEMPERATURE <= 1.0):
            raise ValueError(
                f"TEMPERATURE must be between 0.0 and 1.0, got: {self.TEMPERATURE}"
            )
        if self.MAX_OUTPUT_TOKENS < 512:
            raise ValueError(
                f"MAX_OUTPUT_TOKENS must be at least 512, got: {self.MAX_OUTPUT_TOKENS}"
            )
        if self.THINKING_LEVEL not in (None, "low", "high"):
            raise ValueError(
                f"THINKING_LEVEL must be 'off', 'low', or 'high', got: {self.THINKING_LEVEL}"
            )
        if self.MAX_RETRIES < 1:
            raise ValueError(
                f"MAX_RETRIES must be at least 1, got: {self.MAX_RETRIES}"
            )
        if self.DELAY_BETWEEN_RETRIES < 1:
            raise ValueError(
                f"DELAY_BETWEEN_RETRIES must be at least 1 second, got: {self.DELAY_BETWEEN_RETRIES}"
            )


# Create module-level config instance and validate immediately
config = Config()
config.validate()
