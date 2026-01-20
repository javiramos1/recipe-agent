"""Pre-hooks and guardrails for Recipe Recommendation Agent.

Implements ingredient detection pre-hooks and safety guardrails.

Pre-hook Pipeline:
1. extract_ingredients_pre_hook - Detects ingredients from images (ChatMessage format)
2. PromptInjectionGuardrail - Safety guardrail
"""

from typing import List

from agno.guardrails import PromptInjectionGuardrail

from src.utils.config import config
from src.utils.logger import logger
from src.mcp_tools.ingredients import extract_ingredients_pre_hook


def get_pre_hooks() -> List:
    """Get list of pre-hooks based on configuration.
    
    Returns:
        List of pre-hooks to register with agent in execution order.
        
    Includes:
        - Ingredient extraction (pre-hook mode only)
        - Prompt injection guardrail (enabled by default)
    
    Note: Input is directly ChatMessage schema - no normalization needed.
    """
    hooks: List = []
    
    # Step 1: Add ingredient extraction pre-hook if in pre-hook mode
    if config.IMAGE_DETECTION_MODE == "pre-hook":
        hooks.append(extract_ingredients_pre_hook)
        logger.info("Registered ingredient extraction pre-hook")
    
    # Step 2: Add prompt injection guardrail
    hooks.append(PromptInjectionGuardrail())
    logger.info("Registered prompt injection guardrail")
    
    return hooks