"""Spoonacular MCP initialization with connection validation and retry logic.

This module provides the SpoonacularMCP class for initializing external
Spoonacular MCP tool with proper error handling and exponential backoff retries (async).
"""

import asyncio
from typing import Optional

from agno.tools.mcp import MCPTools
from src.utils.logger import logger


class SpoonacularMCP:
    """Initialize and validate Spoonacular MCP connection.

    Manages connection validation with exponential backoff retry logic
    to handle transient failures gracefully.
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        retry_delays: Optional[list[int]] = None,
    ) -> None:
        """Initialize SpoonacularMCP with configuration.

        Args:
            api_key: Spoonacular API key for authentication.
            max_retries: Maximum number of connection retry attempts (default: 3).
            retry_delays: List of delays in seconds for each retry. If None, defaults to [1, 2, 4].

        Raises:
            ValueError: If api_key is None or empty string.
        """
        if not api_key:
            raise ValueError("SPOONACULAR_API_KEY is required")

        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [1, 2, 4]

    async def initialize(self) -> MCPTools:
        """Initialize MCP with connection validation and retries (async).

        Validates API key and tests connection to Spoonacular MCP server
        using exponential backoff retry logic. Fails fast on startup
        if connection cannot be established.

        Returns:
            MCPTools: Configured MCPTools instance ready for use.

        Raises:
            ValueError: If API key is invalid or missing.
            ConnectionError: If connection fails after all retry attempts.
            Exception: For other initialization failures.
        """
        logger.info("Validating Spoonacular API key...")
        if not self.api_key:
            raise ValueError("SPOONACULAR_API_KEY is required")

        logger.info("Testing connection to Spoonacular MCP...")

        # Retry loop with exponential backoff
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Connection attempt {attempt + 1}/{self.max_retries}...")

                # Create MCPTools instance (this tests the connection)
                # Run in thread pool since MCPTools is synchronous
                mcp_tools = await asyncio.to_thread(
                    MCPTools,
                    command="npx -y spoonacular-mcp",
                    env={"SPOONACULAR_API_KEY": self.api_key},
                )

                logger.info("Spoonacular MCP connected successfully")
                return mcp_tools

            except Exception as e:
                last_exception = e
                logger.debug(f"Connection attempt {attempt + 1} failed: {e}")

                # If this is not the last attempt, retry with delay
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt] if attempt < len(self.retry_delays) else 4
                    logger.warning(
                        f"Connection failed, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        error_msg = f"Failed to connect to Spoonacular MCP after {self.max_retries} attempts"
        logger.error(f"{error_msg}: {last_exception}")
        raise ConnectionError(error_msg)
