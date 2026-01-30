"""Pytest configuration and fixtures for integration tests.

Ensures environment variables are loaded and validates required API keys
before running integration tests.
"""

import os
import pytest
from dotenv import load_dotenv
from pathlib import Path


def pytest_configure(config):
    """Configure pytest and validate environment before running tests.

    This hook runs before test collection, ensuring .env is loaded
    and disabling knowledge/memory features for clean integration testing.
    """
    # Load environment variables from .env (in project root)
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Disable knowledge graph and memory features for integration tests
    # This ensures tests are isolated and don't accumulate state across runs
    os.environ["SEARCH_KNOWLEDGE"] = "false"
    os.environ["UPDATE_KNOWLEDGE"] = "false"
    os.environ["READ_TOOL_CALL_HISTORY"] = "false"
    os.environ["READ_CHAT_HISTORY"] = "false"
    os.environ["ENABLE_USER_MEMORIES"] = "false"
    os.environ["ENABLE_SESSION_SUMMARIES"] = "false"
    os.environ["USE_SPOONACULAR"] = "false"

    # Print note about required API keys
    print("\n" + "=" * 70)
    print("Note: These tests require valid GEMINI_API_KEY")
    print(f"Environment loaded from: {env_path}")
    print("Test configuration:")
    print("  - Knowledge graph: DISABLED")
    print("  - User memories: DISABLED")
    print("  - Session summaries: DISABLED")
    print("  - History access: DISABLED")
    print("  - Spoonacular API: DISABLED")
    print("=" * 70 + "\n")


@pytest.fixture(scope="session", autouse=True)
def check_api_keys():
    """Validate required API keys are available.

    This fixture automatically runs for all test sessions and skips tests
    if required API keys are not configured in .env
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    spoonacular_key = os.getenv("SPOONACULAR_API_KEY")

    if not gemini_key or not spoonacular_key:
        missing = []
        if not gemini_key:
            missing.append("GEMINI_API_KEY")
        if not spoonacular_key:
            missing.append("SPOONACULAR_API_KEY")

        pytest.skip(
            f"Integration tests skipped. Missing API keys: {', '.join(missing)}. Please set these in your .env file.",
            allow_module_level=True,
        )
