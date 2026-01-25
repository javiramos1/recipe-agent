"""Pre-hooks, post-hooks, and tool-hooks for Recipe Recommendation Agent.

Implements ingredient detection pre-hooks, safety guardrails, metadata injection, and response extraction.

Pre-hook Pipeline:
1. extract_ingredients_pre_hook - Detects ingredients from images (ChatMessage format)
2. PromptInjectionGuardrail - Safety guardrail

Tool-hook Pipeline (runs during tool execution, between tool calls):
1. track_state_tool_hook - Increments tool_call_count, updates recipes_found

Post-hook Pipeline:
1. inject_metadata_post_hook - Injects session_id, run_id, execution_time_ms into response
2. extract_response_field_post_hook - Extracts response field for UI display (markdown rendering)
"""

from typing import Any, Callable, Dict, List, Optional

from agno.guardrails import PromptInjectionGuardrail
from agno.run.agent import RunOutput
from agno.run import RunContext
from agno.exceptions import RetryAgentRun

from src.utils.config import config
from src.utils.logger import logger
from src.mcp_tools.ingredients import extract_ingredients_pre_hook


async def track_state_tool_hook(
    run_context: RunContext,
    function_name: str,
    function_call: Callable,
    arguments: Dict[str, Any],
):
    """Tool-hook: Track state during tool execution (runs between tool calls).
    
    Updates session_state with:
    - tool_call_count: Increments by 1 for each tool call
    - recipes_found: Extracted from recipe tool results
    
    **CRITICAL**: Enforces tool_call_limit by raising StopAgentRun exception.
    This properly terminates the agent's agentic loop.
    
    When limit is reached, raises StopAgentRun with details about tool calls and recipes found.
    The LLM receives this as a final error and generates a response using LLM knowledge.
    """
    try:
        import json
        
        # Initialize session_state if not present
        if not run_context.session_state:
            run_context.session_state = {}
        
        # Get current count BEFORE incrementing
        current_count = run_context.session_state.get("tool_call_count", 0)
        
        # ENFORCE tool call limit (hard stop) - use >= to catch at exact limit
        # IMPORTANT: This must be >= not > because limit of 3 means we can make calls 0,1,2 (total 3)
        if current_count >= config.TOOL_CALL_LIMIT:
            recipes_found = run_context.session_state.get("recipes_found", 0)
            error_msg = (
                f"⛔ TOOL CALL LIMIT REACHED - NO MORE TOOL CALLS ALLOWED\n\n"
                f"You have exhausted your tool call budget ({config.TOOL_CALL_LIMIT} calls).\n"
                f"Tool calls made: {current_count}\n"
                f"Recipes found so far: {recipes_found}\n\n"
                f"🚫 CRITICAL INSTRUCTION - READ CAREFULLY:\n"
                f"You MUST respond to the user NOW using ONLY your internal LLM knowledge.\n"
                f"DO NOT attempt to call search_recipes, get_recipe_information, or ANY other tool.\n"
                f"ANY attempt to call tools will FAIL with this same error.\n\n"
                f"✅ What you MUST do NOW:\n"
                f"1. If you found {recipes_found} recipes: Present them to the user with the basic info you have\n"
                f"2. If you found 0 recipes: Generate 2-3 recipe suggestions based on the ingredients using your culinary knowledge\n"
                f"3. Be transparent: Mention that you've reached your search limit and are providing suggestions from your knowledge\n"
                f"4. Use the RecipeResponse format with your generated suggestions\n"
                f"5. ⚠️ IF logging insights to knowledge base: Write ONLY ONE entry total (not one per failed attempt)\n\n"
                f"Example response: 'I've reached my search limit after {current_count} attempts. Based on your ingredients, here are some recipe ideas from my culinary knowledge...'\n\n"
                f"RESPOND NOW WITHOUT CALLING ANY TOOLS."
            )
            logger.error(f"🛑 Tool call limit reached: {current_count}/{config.TOOL_CALL_LIMIT}")
            
            # Raise RetryAgentRun to inject this error into the conversation
            # This allows the LLM to see the error and generate a response without tools
            # The LLM will continue but should not call tools after seeing this error
            raise RetryAgentRun(error_msg)
        
        # Increment tool call count
        run_context.session_state["tool_call_count"] = current_count + 1
        recipes_found = run_context.session_state.get("recipes_found", 0)
        
        logger.info(f"Tool-hook: '{function_name}' | tool_calls={current_count + 1}/{config.TOOL_CALL_LIMIT} | recipes={recipes_found}/{config.MAX_RECIPES}")
        
        # Call the actual tool function
        result = await function_call(**arguments)
        
        # Extract recipe count from recipe tool results
        if function_name in ["search_recipes", "get_recipe_information"]:
            recipes_in_result = _extract_recipe_count(result)
            if recipes_in_result > 0:
                current_recipes = run_context.session_state.get("recipes_found", 0)
                run_context.session_state["recipes_found"] = current_recipes + recipes_in_result
                logger.info(f"✓ Found {recipes_in_result} recipes | total: {current_recipes + recipes_in_result}/{config.MAX_RECIPES}")
        
        return result
    
    except Exception as e:
        logger.warning(f"Tool-hook error in '{function_name}': {e}")
        return await function_call(**arguments)


def _extract_recipe_count(result: Any) -> int:
    """Extract recipe count from tool result. Handles ToolResult wrapping and JSON parsing."""
    import json
    
    # Unwrap ToolResult if needed
    actual_result = result.content if hasattr(result, 'content') else result
    
    # Handle dict with 'recipes' or 'results' keys
    if isinstance(actual_result, dict):
        return len(actual_result.get("recipes", []) or actual_result.get("results", []))
    
    # Handle JSON string
    if isinstance(actual_result, str):
        try:
            parsed = json.loads(actual_result)
            if isinstance(parsed, dict):
                return len(parsed.get("recipes", []) or parsed.get("results", []))
            elif isinstance(parsed, list):
                return len(parsed)
        except (json.JSONDecodeError, ValueError):
            pass
    
    # Handle direct list
    if isinstance(actual_result, list):
        return len(actual_result)
    
    return 0


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


def get_tool_hooks() -> List:
    """Get list of tool-hooks to track state during tool execution.
    
    Returns:
        List of tool-hooks to register with agent.
        
    Tool-hooks run DURING tool execution (between tool calls in the loop),
    allowing real-time state updates visible to the next LLM invocation.
    
    Includes:
        - State tracking (tool_call_count, recipes_found) - always enabled
    """
    hooks: List = []
    
    # Add state tracking tool-hook (always enabled)
    hooks.append(track_state_tool_hook)
    logger.info("Registered state tracking tool-hook (runs during tool execution)")
    
    return hooks


def get_pre_hooks() -> List:
    """Get list of pre-hooks based on configuration.
    
    Returns:
        List of pre-hooks to register with agent in execution order.
        
    Includes:
        - Ingredient extraction (pre-hook mode only)
        - Prompt injection guardrail (enabled by default)
    
    Note: Input is directly ChatMessage schema - no normalization needed.
    Note: Tool call tracking moved to tool-hooks (runs during tool execution).
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


def get_post_hooks(knowledge_base=None) -> List:
    """Get list of post-hooks to process responses after agent execution.
    
    Args:
        knowledge_base: Knowledge instance (optional, not used - agent writes to knowledge via update_knowledge=True)
    
    Returns:
        List of post-hooks to register with agent in execution order.
        
    Includes:
        - Metadata injection (session_id, run_id, execution_time_ms) - always enabled
        - Response field extraction for UI rendering (only if OUTPUT_FORMAT=markdown)
    
    Note: Post-hooks process RunOutput after agent completes.
    Note: Tool call and recipe tracking happen in tool-hooks (runs during tool execution).
    Note: Troubleshooting storage happens automatically via agent's update_knowledge=True setting.
    """
    hooks: List = []
    
    # Always inject metadata (first hook)
    hooks.append(inject_metadata_post_hook)
    logger.info("Registered metadata injection post-hook")
    
    # Only extract response field for markdown output format
    if config.OUTPUT_FORMAT == "markdown":
        hooks.append(extract_response_field_post_hook)
        logger.info("Registered response field extraction post-hook (OUTPUT_FORMAT=markdown)")
    else:
        logger.info("Skipping response field extraction post-hook (OUTPUT_FORMAT=json)")
    
    return hooks