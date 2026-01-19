"""Unit tests for Spoonacular MCP initialization."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.mcp_tools.spoonacular import SpoonacularMCP


class TestMCPInit:
    """Tests for SpoonacularMCP initialization."""

    def test_init_with_valid_key(self) -> None:
        """Test initialization with valid API key."""
        mcp = SpoonacularMCP(api_key="test-key")
        assert mcp.api_key == "test-key"
        assert mcp.max_retries == 3

    def test_init_with_empty_key_raises(self) -> None:
        """Test that empty key raises error."""
        with pytest.raises(ValueError):
            SpoonacularMCP(api_key="")


class TestMCPInitialize:
    """Tests for initialize method."""

    @pytest.mark.asyncio
    @patch("src.mcp_tools.spoonacular.MCPTools")
    @patch("src.mcp_tools.spoonacular.asyncio.to_thread", new_callable=AsyncMock)
    async def test_initialize_success(self, mock_to_thread, mock_mcp: Mock) -> None:
        """Test successful initialization."""
        mock_instance = MagicMock()
        mock_to_thread.return_value = mock_instance
        
        mcp = SpoonacularMCP(api_key="test")
        result = await mcp.initialize()
        
        assert result == mock_instance

    @pytest.mark.asyncio
    @patch("src.mcp_tools.spoonacular.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.mcp_tools.spoonacular.asyncio.to_thread", new_callable=AsyncMock)
    async def test_initialize_with_retries(self, mock_to_thread: Mock, mock_sleep: Mock) -> None:
        """Test initialization with retries."""
        mock_instance = MagicMock()
        mock_to_thread.side_effect = [ConnectionError(), ConnectionError(), mock_instance]
        
        mcp = SpoonacularMCP(api_key="test", max_retries=3)
        result = await mcp.initialize()
        
        assert result == mock_instance
        assert mock_to_thread.call_count == 3
