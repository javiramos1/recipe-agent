"""Pre-hooks and post-hooks for Recipe Recommendation Agent.

Implements ingredient detection pre-hooks, safety guardrails, metadata injection, and response extraction.

Pre-hook Pipeline:
1. extract_ingredients_pre_hook - Detects ingredients from images (ChatMessage format)
2. PromptInjectionGuardrail - Safety guardrail

Post-hook Pipeline:
1. inject_metadata_post_hook - Injects session_id, run_id, execution_time_ms into response
2. store_troubleshooting_post_hook - Stores troubleshooting findings to knowledge base
3. extract_response_field_post_hook - Extracts response field for UI display (markdown rendering)
"""

from typing import List, Optional

from agno.guardrails import PromptInjectionGuardrail
from agno.run.agent import RunOutput

from src.utils.config import config
from src.utils.logger import logger
from src.mcp_tools.ingredients import extract_ingredients_pre_hook


def inject_metadata_post_hook(
    run_output: RunOutput,
    session=None,
    user_id: Optional[str] = None,
    debug_mode: Optional[bool] = None,
) -> None:
    """Post-hook: Inject session_id, run_id, and execution_time_ms into RecipeResponse.
    
    Extracts metadata from RunOutput and adds it to the structured response.
    This ensures the RecipeResponse contains proper session tracking and performance metrics.
    """
    try:
        if not run_output.content:
            return
        
        # Extract metadata from RunOutput
        session_id = getattr(run_output, 'session_id', None)
        run_id = getattr(run_output, 'run_id', None)
        
        # Calculate execution time from metrics
        execution_time_ms = 0
        if hasattr(run_output, 'metrics') and run_output.metrics:
            # Metrics object has time_taken_seconds
            time_taken = getattr(run_output.metrics, 'time_taken_seconds', None)
            if time_taken:
                execution_time_ms = int(time_taken * 1000)
        
        # Inject into RecipeResponse content
        if hasattr(run_output.content, '__dict__'):
            # Pydantic model
            if session_id:
                run_output.content.session_id = session_id
            if run_id:
                run_output.content.run_id = run_id
            if execution_time_ms > 0:
                run_output.content.execution_time_ms = execution_time_ms
            logger.info(f"Post-hook: Injected metadata (session_id={session_id}, run_id={run_id}, execution_time_ms={execution_time_ms})")
        elif isinstance(run_output.content, dict):
            # Dict representation
            if session_id:
                run_output.content['session_id'] = session_id
            if run_id:
                run_output.content['run_id'] = run_id
            if execution_time_ms > 0:
                run_output.content['execution_time_ms'] = execution_time_ms
            logger.info(f"Post-hook: Injected metadata into dict (session_id={session_id}, run_id={run_id})")
    except Exception as e:
        logger.warning(f"Post-hook failed to inject metadata: {e}")


def store_troubleshooting_post_hook(
    run_output: RunOutput,
    session=None,
    user_id: Optional[str] = None,
    debug_mode: Optional[bool] = None,
) -> None:
    """Post-hook: Store troubleshooting findings to knowledge base.
    
    If troubleshooting field is populated with error/retry info,
    add it to the agent's knowledge base for future learning.
    """
    try:
        if not run_output.content:
            return
        
        troubleshooting = None
        
        # Get troubleshooting field from RecipeResponse
        if hasattr(run_output.content, "troubleshooting"):
            troubleshooting = getattr(run_output.content, "troubleshooting", None)
        elif isinstance(run_output.content, dict):
            troubleshooting = run_output.content.get("troubleshooting")
        
        # If troubleshooting info exists, log it (knowledge base persistence handled by agent)
        if troubleshooting and troubleshooting.strip():
            logger.info(f"Post-hook: Troubleshooting recorded - {troubleshooting[:100]}...")
        else:
            logger.debug("Post-hook: No troubleshooting findings to store")
    except Exception as e:
        logger.warning(f"Post-hook failed to process troubleshooting: {e}")


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
        - Metadata injection (session_id, run_id, execution_time_ms) - always enabled
        - Troubleshooting storage to knowledge base - when troubleshooting field populated
        - Response field extraction for UI rendering (only if OUTPUT_FORMAT=markdown)
    
    Note: Post-hooks process RunOutput after agent completes.
    """
    hooks: List = []
    
    # Always inject metadata first (before UI rendering)
    hooks.append(inject_metadata_post_hook)
    logger.info("Registered metadata injection post-hook")
    
    # Store troubleshooting findings to knowledge base
    hooks.append(store_troubleshooting_post_hook)
    logger.info("Registered troubleshooting storage post-hook")
    
    # Only extract response field for markdown output format
    if config.OUTPUT_FORMAT == "markdown":
        hooks.append(extract_response_field_post_hook)
        logger.info("Registered response field extraction post-hook (OUTPUT_FORMAT=markdown)")
    else:
        logger.info("Skipping response field extraction post-hook (OUTPUT_FORMAT=json)")
    
    return hooks