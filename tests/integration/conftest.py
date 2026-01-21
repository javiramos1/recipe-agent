"""Pytest configuration and fixtures for integration tests.

Ensures environment variables are loaded and validates required API keys
before running integration tests.
"""

import os
import pytest
from dotenv import load_dotenv


def pytest_configure(config):
    """Configure pytest and validate environment before running tests.
    
    This hook runs before test collection, ensuring .env is loaded
    and printing the note about required API keys.
    """
    # Load environment variables from .env
    load_dotenv()
    
    # Print note about required API keys
    print("\n" + "=" * 70)
    print("Note: These tests require valid GEMINI_API_KEY and SPOONACULAR_API_KEY")
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
            f"Integration tests skipped. Missing API keys: {', '.join(missing)}. "
            f"Please set these in your .env file.",
            allow_module_level=False
        )
