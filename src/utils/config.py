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
        self.SPOONACULAR_API_KEY: str = os.getenv("SPOONACULAR_API_KEY", "")
        # Default: gemini-3-flash-preview (fast, cost-effective)
        # For best results: use gemini-3-pro-preview for complex recipe reasoning
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        # Image Detection Model: separate model optimized for vision tasks
        # Default: gemini-3-flash-preview (fast, cost-effective for images)
        # For better accuracy: use gemini-3-pro-preview for complex image analysis
        self.IMAGE_DETECTION_MODEL: str = os.getenv("IMAGE_DETECTION_MODEL", "gemini-3-flash-preview")
        self.PORT: int = int(os.getenv("PORT", "7777"))
        self.MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "3"))
        self.MAX_RECIPES: int = int(os.getenv("MAX_RECIPES", "3"))
        self.MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
        self.MIN_INGREDIENT_CONFIDENCE: float = float(os.getenv("MIN_INGREDIENT_CONFIDENCE", "0.7"))
        self.IMAGE_DETECTION_MODE: str = os.getenv("IMAGE_DETECTION_MODE", "pre-hook")
        self.COMPRESS_IMG: bool = os.getenv("COMPRESS_IMG", "true").lower() in ("true", "1", "yes")
        self.OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "json")
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        # Tracing Configuration
        self.ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "true").lower() in ("true", "1", "yes")
        self.TRACING_DB_TYPE: str = os.getenv("TRACING_DB_TYPE", "sqlite")
        self.TRACING_DB_FILE: str = os.getenv("TRACING_DB_FILE", "agno_traces.db")
        # Tool Call Limit: Maximum number of tool calls agent can make per request
        self.TOOL_CALL_LIMIT: int = int(os.getenv("TOOL_CALL_LIMIT", "5"))
        # LLM Model Parameters
        # Temperature: Controls randomness (0.0 = deterministic, 1.0 = max randomness)
        # For recipes: 0.3 balances creativity with consistency
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
        # Max Output Tokens: Maximum length of model response
        # For recipes: 2048 is sufficient for full recipe with instructions
        self.MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))
        # Thinking Level: Enables extended thinking for complex reasoning
        # Options: "low", "high" - Recipe recommendations benefit from low/high thinking
        # "low" = fastest (no extended thinking), "high" = slowest but most thorough
        self.THINKING_LEVEL: str = os.getenv("THINKING_LEVEL", "low")
        
        # Agent Retry Configuration - handles transient API failures gracefully
        # MAX_RETRIES: Number of retry attempts for failed API calls (exponential backoff)
        self.MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
        # DELAY_BETWEEN_RETRIES: Initial delay in seconds (doubled each retry if exponential_backoff=True)
        self.DELAY_BETWEEN_RETRIES: int = int(os.getenv("DELAY_BETWEEN_RETRIES", "2"))
        # EXPONENTIAL_BACKOFF: Enable exponential backoff for rate limit handling
        self.EXPONENTIAL_BACKOFF: bool = os.getenv("EXPONENTIAL_BACKOFF", "true").lower() in ("true", "1", "yes")
        
        # Agent Memory & History Settings - control context enrichment and knowledge management
        # ADD_HISTORY_TO_CONTEXT: Include conversation history in LLM context for coherence
        self.ADD_HISTORY_TO_CONTEXT: bool = os.getenv("ADD_HISTORY_TO_CONTEXT", "true").lower() in ("true", "1", "yes")
        # READ_TOOL_CALL_HISTORY: Give LLM access to previous tool calls for continuity
        self.READ_TOOL_CALL_HISTORY: bool = os.getenv("READ_TOOL_CALL_HISTORY", "true").lower() in ("true", "1", "yes")
        # UPDATE_KNOWLEDGE: Allow LLM to add learnings to knowledge base
        self.UPDATE_KNOWLEDGE: bool = os.getenv("UPDATE_KNOWLEDGE", "true").lower() in ("true", "1", "yes")
        # READ_CHAT_HISTORY: Provide dedicated tool for LLM to query chat history
        self.READ_CHAT_HISTORY: bool = os.getenv("READ_CHAT_HISTORY", "true").lower() in ("true", "1", "yes")
        # ENABLE_USER_MEMORIES: Store and track user preferences for personalization
        self.ENABLE_USER_MEMORIES: bool = os.getenv("ENABLE_USER_MEMORIES", "true").lower() in ("true", "1", "yes")
        # ENABLE_SESSION_SUMMARIES: Auto-summarize sessions for context compression
        self.ENABLE_SESSION_SUMMARIES: bool = os.getenv("ENABLE_SESSION_SUMMARIES", "true").lower() in ("true", "1", "yes")
        # COMPRESS_TOOL_RESULTS: Compress tool outputs to reduce context size
        self.COMPRESS_TOOL_RESULTS: bool = os.getenv("COMPRESS_TOOL_RESULTS", "true").lower() in ("true", "1", "yes")
        # ADD_SESSION_STATE_TO_CONTEXT: Inject tool_call_count and recipes_found into LLM context between calls
        self.ADD_SESSION_STATE_TO_CONTEXT: bool = os.getenv("ADD_SESSION_STATE_TO_CONTEXT", "true").lower() in ("true", "1", "yes")
        # SEARCH_KNOWLEDGE: Give LLM ability to search knowledge base during reasoning
        self.SEARCH_KNOWLEDGE: bool = os.getenv("SEARCH_KNOWLEDGE", "true").lower() in ("true", "1", "yes")

    def validate(self) -> None:
        """Validate required configuration.

        Raises:
            ValueError: If required API keys are missing or invalid values provided.
        """
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        if not self.SPOONACULAR_API_KEY:
            raise ValueError("SPOONACULAR_API_KEY environment variable is required")
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
        if self.THINKING_LEVEL not in ("off", "low", "high"):
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
