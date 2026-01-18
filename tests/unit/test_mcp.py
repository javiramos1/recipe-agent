"""Unit tests for Spoonacular MCP initialization."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from mcp_tools.spoonacular import SpoonacularMCP


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

    @patch("mcp_tools.spoonacular.MCPTools")
    def test_initialize_success(self, mock_mcp: Mock) -> None:
        """Test successful initialization."""
        mock_instance = MagicMock()
        mock_mcp.return_value = mock_instance
        
        mcp = SpoonacularMCP(api_key="test")
        result = mcp.initialize()
        
        assert result == mock_instance

    @patch("mcp_tools.spoonacular.time.sleep")
    @patch("mcp_tools.spoonacular.MCPTools")
    def test_initialize_with_retries(self, mock_mcp: Mock, mock_sleep: Mock) -> None:
        """Test initialization with retries."""
        mock_instance = MagicMock()
        mock_mcp.side_effect = [ConnectionError(), ConnectionError(), mock_instance]
        
        mcp = SpoonacularMCP(api_key="test", max_retries=3)
        result = mcp.initialize()
        
        assert result == mock_instance
        assert mock_mcp.call_count == 3
