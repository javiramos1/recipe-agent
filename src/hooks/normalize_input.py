"""Input normalization pre-hook for unified ChatMessage format.

Handles dual-path input from:
1. query.py (direct Python API with ChatMessage schema)
2. Agno UI (HTTP FormData with JSON-stringified message)

Result: All downstream pre-hooks receive consistent ChatMessage format.
"""

import json

from src.utils.logger import logger


async def normalize_input_pre_hook(
    run_input,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """Normalize input into unified ChatMessage format.

    Detects input source and converts to consistent format:
    - If already ChatMessage: Pass through (message and images attributes exist)
    - If FormData JSON string: Parse and normalize to ChatMessage attributes
    - If plain text: Wrap in ChatMessage format

    After this pre-hook, all downstream hooks can assume:
    - run_input.message exists (str)
    - run_input.images exists (list)

    Args:
        run_input: Agno RunInput object (may contain message/images or raw input_content)
        session: Agno AgentSession (automatically injected by Agno framework)
        user_id: Optional user ID (automatically injected by Agno framework)
        debug_mode: Optional debug flag (automatically injected by Agno framework)

    Returns:
        None (modifies run_input in-place to have message/images attributes)
    """
    try:
        session_id = getattr(session, "session_id", None) if session else None
        logger.info(
            f"Pre-hook: normalize_input_pre_hook(session_id={session_id}, "
            f"user_id={user_id}, debug_mode={debug_mode})"
        )

        message_text = ""
        images = []

        # DETECTION: Determine which source this came from
        if hasattr(run_input, "message") and isinstance(run_input.message, str):
            # Already normalized: message is a string attribute (from ChatMessage schema)
            logger.debug("Detected: Already normalized ChatMessage schema")
            message_text = run_input.message or ""
            images = getattr(run_input, "images", None) or []
        else:
            # Try to parse input_content as JSON (FormData from Agno UI)
            input_content = getattr(run_input, "input_content", "")
            logger.debug(f"Input content type: {type(input_content)}")

            try:
                message_data = json.loads(input_content)
                if isinstance(message_data, dict):
                    message_text = message_data.get("message", "")
                    images = message_data.get("images", []) or []
                    logger.debug("Detected: FormData JSON string from Agno UI")
            except (json.JSONDecodeError, ValueError, TypeError):
                # Not JSON: treat input_content as plain text message
                message_text = str(input_content)
                logger.debug("Detected: Plain text message")

        # NORMALIZE: Ensure run_input has message and images attributes for downstream hooks
        run_input.message = message_text
        run_input.images = images or []

        logger.debug(
            f"Normalized input: message={len(message_text)} chars, "
            f"images={len(images)} items"
        )

    except Exception as e:
        # Pre-hooks must be resilient - log but don't crash
        logger.warning(f"Input normalization pre-hook failed: {e}")
