"""Pre-hooks and post-hooks for Recipe Recommendation Agent.

Implements ingredient detection pre-hooks, safety guardrails, and response extraction post-hooks.

Pre-hook Pipeline:
1. extract_ingredients_pre_hook - Detects ingredients from images (ChatMessage format)
2. PromptInjectionGuardrail - Safety guardrail

Post-hook Pipeline:
1. extract_response_field_post_hook - Extracts response field for UI display (markdown rendering)
"""

from typing import List, Optional

from agno.guardrails import PromptInjectionGuardrail
from agno.run.agent import RunOutput

from src.utils.config import config
from src.utils.logger import logger
from src.mcp_tools.ingredients import extract_ingredients_pre_hook


def extract_response_field_post_hook(
    run_output: RunOutput,
    session=None,
    user_id: Optional[str] = None,
    debug_mode: Optional[bool] = None,
) -> None:
    """Post-hook: Extract response field from RecipeResponse for UI display.
    
    Replaces the full structured output with just the markdown response field
    so the Agno UI displays the response text instead of raw JSON.
    """
    try:
        if not run_output.content:
            return
        
        response_text = None
        
        # Try to get response field from RecipeResponse Pydantic model
        if hasattr(run_output.content, "response"):
            response_text = getattr(run_output.content, "response", None)
        # Try dict representation
        elif isinstance(run_output.content, dict):
            response_text = run_output.content.get("response")
        # Try JSON string
        elif isinstance(run_output.content, str):
            try:
                import json
                content_dict = json.loads(run_output.content)
                response_text = content_dict.get("response")
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Replace content with markdown response for UI rendering
        if response_text:
            run_output.content = response_text
            logger.info("Post-hook: Extracted response field for UI rendering")
    except Exception as e:
        logger.warning(f"Post-hook failed to extract response field: {e}")


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


def get_post_hooks() -> List:
    """Get list of post-hooks to process responses after agent execution.
    
    Returns:
        List of post-hooks to register with agent in execution order.
        
    Includes:
        - Response field extraction for UI rendering (only if OUTPUT_FORMAT=markdown)
    
    Note: Post-hooks process RunOutput after agent completes.
    """
    hooks: List = []
    
    # Only extract response field for markdown output format
    if config.OUTPUT_FORMAT == "markdown":
        hooks.append(extract_response_field_post_hook)
        logger.info("Registered response field extraction post-hook (OUTPUT_FORMAT=markdown)")
    else:
        logger.info("Skipping response field extraction post-hook (OUTPUT_FORMAT=json)")
    
    return hooks