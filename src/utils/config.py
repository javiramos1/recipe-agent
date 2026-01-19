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
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.PORT: int = int(os.getenv("PORT", "7777"))
        self.MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "3"))
        self.MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
        self.MIN_INGREDIENT_CONFIDENCE: float = float(os.getenv("MIN_INGREDIENT_CONFIDENCE", "0.7"))
        self.IMAGE_DETECTION_MODE: str = os.getenv("IMAGE_DETECTION_MODE", "pre-hook")
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

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


# Create module-level config instance and validate immediately
config = Config()
config.validate()
