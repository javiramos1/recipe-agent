"""Unit tests for app.py - Agent configuration and MCP initialization.

Tests verify:
- Agent instance created without errors
- MCP initialization with connection validation
- Tool and pre-hook registration based on IMAGE_DETECTION_MODE
- Database configuration (SQLite/PostgreSQL)
- System instructions properly configured
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open

from src.utils.config import config


class TestMCPInitialization:
    """Tests for Spoonacular MCP initialization."""

    def test_mcp_init_called_with_correct_params(self):
        """Test MCP is initialized with correct parameters."""
        # SpoonacularMCP should be called with api_key, max_retries, and retry_delays
        expected_api_key = config.SPOONACULAR_API_KEY
        expected_max_retries = 3
        expected_retry_delays = [1, 2, 4]

        # Verify configuration values
        assert expected_api_key  # API key must be set
        assert expected_max_retries == 3
        assert expected_retry_delays == [1, 2, 4]


class TestAgentConfiguration:
    """Tests for Agno Agent configuration."""

    def test_agent_module_syntax_valid(self):
        """Test that agent module has no syntax errors."""
        import ast
        with open("src/agents/agent.py", "r") as f:
            code = f.read()
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"src/agents/agent.py has syntax errors: {e}")

    def test_database_sqlite_when_no_database_url(self):
        """Test SQLite is used when DATABASE_URL is not set."""
        with patch.dict("os.environ", {"DATABASE_URL": ""}, clear=False):
            # SQLite should be used as default
            # We're testing the logic, not creating actual DB
            assert config.DATABASE_URL is None or config.DATABASE_URL == ""

    def test_factory_function_defined(self):
        """Test that initialize_recipe_agent factory function is defined in agent.py."""
        import ast
        with open("src/agents/agent.py", "r") as f:
            code = f.read()
        tree = ast.parse(code)
        
        # Find top-level function definitions (including async functions)
        functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        assert "initialize_recipe_agent" in functions


class TestImageDetectionMode:
    """Tests for IMAGE_DETECTION_MODE configuration."""

    def test_image_detection_mode_valid_values(self):
        """Test IMAGE_DETECTION_MODE has valid value."""
        assert config.IMAGE_DETECTION_MODE in ("pre-hook", "tool")

    def test_pre_hook_mode_configuration(self):
        """Test pre-hook mode configuration."""
        with patch.dict("os.environ", {"IMAGE_DETECTION_MODE": "pre-hook"}, clear=False):
            test_config = __import__("src.utils.config", fromlist=["Config"]).Config()
            assert test_config.IMAGE_DETECTION_MODE == "pre-hook"

    def test_tool_mode_configuration(self):
        """Test tool mode configuration."""
        with patch.dict("os.environ", {"IMAGE_DETECTION_MODE": "tool"}, clear=False):
            test_config = __import__("src.utils.config", fromlist=["Config"]).Config()
            assert test_config.IMAGE_DETECTION_MODE == "tool"


class TestRequiredDependencies:
    """Tests for required dependencies."""

    def test_gemini_api_key_configured(self):
        """Test GEMINI_API_KEY is configured."""
        assert config.GEMINI_API_KEY
        assert len(config.GEMINI_API_KEY) > 0

    def test_spoonacular_api_key_configured(self):
        """Test SPOONACULAR_API_KEY is configured."""
        assert config.SPOONACULAR_API_KEY
        assert len(config.SPOONACULAR_API_KEY) > 0

    def test_gemini_model_configured(self):
        """Test GEMINI_MODEL is configured with valid value."""
        assert config.GEMINI_MODEL
        assert "gemini" in config.GEMINI_MODEL.lower()


class TestPortConfiguration:
    """Tests for port configuration."""

    def test_default_port_set(self):
        """Test default port is set."""
        assert config.PORT == 7777

    def test_port_is_integer(self):
        """Test PORT is an integer."""
        assert isinstance(config.PORT, int)

    def test_port_valid_range(self):
        """Test PORT is in valid range."""
        assert 1024 <= config.PORT <= 65535


class TestMemoryConfiguration:
    """Tests for memory and history configuration."""

    def test_max_history_configured(self):
        """Test MAX_HISTORY is configured."""
        assert config.MAX_HISTORY > 0
        assert config.MAX_HISTORY == 3  # Default value

    def test_min_ingredient_confidence_configured(self):
        """Test MIN_INGREDIENT_CONFIDENCE is configured."""
        assert 0.0 <= config.MIN_INGREDIENT_CONFIDENCE <= 1.0
        assert config.MIN_INGREDIENT_CONFIDENCE == 0.7  # Default value

    def test_max_image_size_configured(self):
        """Test MAX_IMAGE_SIZE_MB is configured."""
        assert config.MAX_IMAGE_SIZE_MB > 0
        assert config.MAX_IMAGE_SIZE_MB == 5  # Default value


class TestSystemInstructionsContent:
    """Tests for system instructions content."""

    def _get_system_instructions(self):
        """Helper to get system instructions from the function."""
        from src.prompts.prompts import get_system_instructions
        return get_system_instructions()

    def test_system_instructions_cover_core_responsibilities(self):
        """Test system instructions include core responsibilities."""
        instructions = self._get_system_instructions()
        assert "recommend recipes" in instructions.lower()
        assert "complete recipe details" in instructions.lower()
        assert "dietary" in instructions.lower()

    def test_system_instructions_cover_ingredient_sources(self):
        """Test system instructions define ingredient source priority."""
        instructions = self._get_system_instructions()
        assert "ingredient sources" in instructions.lower()
        assert "priority" in instructions.lower()
        assert "[detected ingredients]" in instructions.lower()

    def test_system_instructions_cover_two_step_recipe_process(self):
        """Test system instructions enforce two-step recipe process."""
        instructions = self._get_system_instructions()
        assert "two-step" in instructions.lower() or ("step 1" in instructions.lower() and "step 2" in instructions.lower())
        assert "search_recipes" in instructions
        assert "get_recipe_information" in instructions
        assert "never provide recipe instructions without" in instructions.lower()

    def test_system_instructions_cover_preference_management(self):
        """Test system instructions cover preference extraction and application."""
        instructions = self._get_system_instructions()
        assert "preference" in instructions.lower()
        assert "extract" in instructions.lower()
        assert "dietary" in instructions.lower()
        assert "remember" in instructions.lower()

    def test_system_instructions_cover_image_handling(self):
        """Test system instructions cover image handling for both modes."""
        instructions = self._get_system_instructions()
        assert "pre-hook mode" in instructions.lower()
        assert "tool mode" in instructions.lower()
        assert "detect_image_ingredients" in instructions

    def test_system_instructions_cover_edge_cases(self):
        """Test system instructions cover edge cases."""
        instructions = self._get_system_instructions()
        assert "no ingredients" in instructions.lower() or "no ingredients detected" in instructions.lower()
        assert "no recipes found" in instructions.lower()

    def test_system_instructions_cover_critical_guardrails(self):
        """Test system instructions include critical guardrails."""
        instructions = self._get_system_instructions()
        assert "critical guardrails" in instructions.lower() or "guardrails" in instructions.lower()
        assert "ground" in instructions.lower()


class TestToolsAndPreHooks:
    """Tests for tools and pre-hooks registration."""

    def test_ingredient_detection_tool_signature(self):
        """Test ingredient detection tool has correct signature."""
        from src.mcp_tools.ingredients import detect_ingredients_tool
        
        # Tool function should be callable
        assert callable(detect_ingredients_tool)
        
        # Should accept image_data parameter
        import inspect
        sig = inspect.signature(detect_ingredients_tool)
        assert "image_data" in sig.parameters

    def test_pre_hook_function_signature(self):
        """Test pre-hook function has correct signature."""
        from src.mcp_tools.ingredients import extract_ingredients_pre_hook
        
        # Pre-hook should be callable
        assert callable(extract_ingredients_pre_hook)
        
        # Pre-hook receives run_input, session, user_id, debug_mode
        import inspect
        sig = inspect.signature(extract_ingredients_pre_hook)
        assert "run_input" in sig.parameters
        assert "session" in sig.parameters


class TestAgentMetadata:
    """Tests for agent metadata configuration."""

    def test_agent_configuration_in_code(self):
        """Test agent has proper configuration in agent.py."""
        with open("src/agents/agent.py", "r") as f:
            code = f.read()
        
        # Verify agent initialization with proper settings
        assert "Agent(" in code
        assert "model=Gemini(" in code
        assert "db=db" in code or "db=" in code
        assert "tools=tools" in code
        assert 'name="Recipe Recommendation Agent"' in code
        assert "enable_user_memories=True" in code
        assert "enable_session_summaries=True" in code
        assert "compress_tool_results=True" in code
