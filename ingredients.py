"""Pre-hook for ingredient extraction from images using Gemini vision API.

This module provides the extract_ingredients_pre_hook function that:
- Runs BEFORE the Agno agent processes a request
- Extracts ingredients from uploaded images using Gemini vision API
- Appends detected ingredients to the user message as clean text
- Clears images from input to prevent agent re-processing
- Handles errors gracefully without crashing
"""

import json
import re
from typing import Optional

import filetype
from google import genai
from google.genai import types

from config import config
from logger import logger


def fetch_image_bytes(image_source: str | bytes) -> Optional[bytes]:
    """Fetch image bytes from URL or return directly if bytes.

    Args:
        image_source: Either a URL string or bytes object.

    Returns:
        Image bytes if successful, None on failure.
    """
    if isinstance(image_source, bytes):
        return image_source

    if isinstance(image_source, str):
        try:
            import urllib.request

            with urllib.request.urlopen(image_source, timeout=10) as response:
                return response.read()
        except Exception as e:
            logger.warning(f"Failed to fetch image from URL: {image_source}, error: {e}")
            return None

    return None


def validate_image_format(image_bytes: bytes) -> bool:
    """Validate image format (JPEG or PNG only).

    Args:
        image_bytes: Raw image bytes.

    Returns:
        True if valid format, False otherwise.
    """
    kind = filetype.guess(image_bytes)
    if kind is None or kind.extension not in ("jpg", "jpeg", "png"):
        logger.warning(f"Invalid image format: {kind}. Only JPEG and PNG supported.")
        return False
    return True


def validate_image_size(image_bytes: bytes) -> bool:
    """Validate image size against MAX_IMAGE_SIZE_MB.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        True if size valid, False if exceeds limit.
    """
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > config.MAX_IMAGE_SIZE_MB:
        logger.warning(f"Image size {size_mb:.2f}MB exceeds limit of {config.MAX_IMAGE_SIZE_MB}MB")
        return False
    return True


def parse_gemini_response(response_text: str) -> Optional[dict]:
    """Parse JSON from Gemini response, handling text before/after JSON.

    Args:
        response_text: Raw response text from Gemini API.

    Returns:
        Parsed dict with 'ingredients' and 'confidence_scores', or None on parse failure.
    """
    try:
        # Try direct JSON parse first
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text (Gemini might add explanatory text)
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse JSON from Gemini response")
    return None


def extract_ingredients_from_image(image_bytes: bytes) -> Optional[dict]:
    """Call Gemini vision API to extract ingredients from image.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        Dict with 'ingredients' list and 'confidence_scores' dict, or None on failure.
    """
    try:
        # Determine MIME type based on image format
        kind = filetype.guess(image_bytes)
        if kind is None:
            logger.warning("Unable to determine image format")
            return None

        mime_type = "image/jpeg" if kind.extension in ("jpg", "jpeg") else "image/png"

        # Initialize Gemini client
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # Call vision API with JSON response format
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                "Extract all food ingredients from this image. Return ONLY valid JSON with 'ingredients' list (strings) and 'confidence_scores' dict mapping ingredient name to confidence (0.0-1.0). Example: {\"ingredients\": [\"tomato\", \"basil\"], \"confidence_scores\": {\"tomato\": 0.95, \"basil\": 0.88}}",
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )

        # Parse response
        result = parse_gemini_response(response.text)
        if not result:
            return None

        # Validate response structure
        if not isinstance(result.get("ingredients"), list):
            logger.warning("Invalid response structure: 'ingredients' is not a list")
            return None

        if not isinstance(result.get("confidence_scores"), dict):
            logger.warning("Invalid response structure: 'confidence_scores' is not a dict")
            return None

        return result

    except Exception as e:
        logger.warning(f"Failed to extract ingredients from image: {e}")
        return None


def filter_ingredients_by_confidence(
    ingredients: list[str], confidence_scores: dict[str, float]
) -> list[str]:
    """Filter ingredients by MIN_INGREDIENT_CONFIDENCE threshold.

    Args:
        ingredients: List of ingredient names.
        confidence_scores: Dict mapping ingredient name to confidence score.

    Returns:
        Filtered list of ingredients with confidence >= threshold.
    """
    filtered = [
        ingredient
        for ingredient in ingredients
        if confidence_scores.get(ingredient, 0.0) >= config.MIN_INGREDIENT_CONFIDENCE
    ]

    if len(filtered) < len(ingredients):
        logger.debug(
            f"Filtered ingredients: {len(ingredients)} → {len(filtered)} "
            f"(confidence threshold: {config.MIN_INGREDIENT_CONFIDENCE})"
        )

    return filtered


def extract_ingredients_pre_hook(
    run_input,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """Pre-hook: Extract ingredients from images before agent processes request.

    This function:
    1. Checks for images in the request
    2. Calls Gemini vision API to extract ingredients
    3. Filters by confidence threshold
    4. Appends detected ingredients to user message as text
    5. Clears images from input (prevents agent re-processing)

    Args:
        run_input: Agno RunInput object containing user message and images.
        session: Agno AgentSession providing current session context.
            Automatically injected by Agno framework during pre-hook execution.
        user_id: Optional contextual user ID for the current run.
            Automatically injected by Agno framework if provided during agent.run().
        debug_mode: Optional boolean indicating if debug mode is enabled.
            Automatically injected by Agno framework based on agent configuration.

    Returns:
        None (modifies run_input in-place).

    Note:
        All parameters (session, user_id, debug_mode) are part of the Agno pre-hook
        contract and are automatically injected by the Agno framework. They enable
        future extensibility (e.g., user-specific confidence thresholds, session
        state tracking) even if not currently used in the implementation.
    """
    try:
        # Log pre-hook execution context
        session_id = getattr(session, "session_id", None) if session else None
        logger.info(
            f"Pre-hook: extract_ingredients_pre_hook(session_id={session_id}, "
            f"user_id={user_id}, debug_mode={debug_mode})"
        )

        # Check for images in input
        images = getattr(run_input, "images", [])
        if not images:
            logger.debug("No images in request, skipping ingredient extraction")
            return

        logger.debug(f"Found {len(images)} image(s), extracting ingredients...")

        all_ingredients = []
        for idx, image in enumerate(images):
            # Get image bytes
            image_bytes = None
            if hasattr(image, "url"):
                image_bytes = fetch_image_bytes(image.url)
            elif hasattr(image, "content"):
                image_bytes = fetch_image_bytes(image.content)

            if not image_bytes:
                logger.warning(f"Image {idx + 1}: Failed to get image bytes")
                continue

            # Validate image
            if not validate_image_format(image_bytes):
                continue

            if not validate_image_size(image_bytes):
                continue

            # Extract ingredients from image
            result = extract_ingredients_from_image(image_bytes)
            if not result:
                logger.warning(f"Image {idx + 1}: Failed to extract ingredients")
                continue

            # Filter by confidence
            ingredients = filter_ingredients_by_confidence(
                result.get("ingredients", []), result.get("confidence_scores", {})
            )

            if ingredients:
                all_ingredients.extend(ingredients)
                logger.debug(f"Image {idx + 1}: Extracted {len(ingredients)} ingredients")
            else:
                logger.warning(f"Image {idx + 1}: No ingredients with sufficient confidence")

        # Append detected ingredients to message
        if all_ingredients:
            unique_ingredients = list(dict.fromkeys(all_ingredients))  # Remove duplicates, preserve order
            ingredient_text = ", ".join(unique_ingredients)
            original_message = getattr(run_input, "input_content", "")
            run_input.input_content = (
                f"{original_message}\n\n[Detected Ingredients] {ingredient_text}"
            )
            logger.info(f"Appended {len(unique_ingredients)} detected ingredients to message")

        # Clear images to prevent agent re-processing
        run_input.images = []

    except Exception as e:
        # Pre-hooks must be resilient - log but don't crash
        logger.warning(f"Ingredient extraction pre-hook failed: {e}")


def extract_ingredients_with_retries(
    image_bytes: bytes, max_retries: int = 3
) -> Optional[dict]:
    """Call Gemini vision API with exponential backoff retry logic.

    Retries on transient failures (network errors, rate limits, 5xx errors).
    Does NOT retry on permanent failures (invalid API key, malformed request).

    Args:
        image_bytes: Raw image bytes to process.
        max_retries: Maximum number of retry attempts (default: 3).

    Returns:
        Dict with 'ingredients' and 'confidence_scores', or None if all retries failed.
    """
    retry_count = 0
    delay_seconds = 1

    while retry_count < max_retries:
        try:
            result = extract_ingredients_from_image(image_bytes)
            if result:
                return result
            # If result is None but no exception, retry (might be transient API issue)
            retry_count += 1
            if retry_count < max_retries:
                logger.debug(f"Retrying ingredient extraction (attempt {retry_count + 1}/{max_retries}) after {delay_seconds}s")
                import time
                time.sleep(delay_seconds)
                delay_seconds *= 2  # Exponential backoff
        except Exception as e:
            # Check if error is transient or permanent
            error_str = str(e).lower()
            is_transient = any(
                keyword in error_str
                for keyword in ["timeout", "connection", "429", "500", "503", "502", "retryable"]
            )

            if is_transient and retry_count < max_retries - 1:
                retry_count += 1
                logger.debug(
                    f"Transient error detected, retrying (attempt {retry_count + 1}/{max_retries}) "
                    f"after {delay_seconds}s: {e}"
                )
                import time
                time.sleep(delay_seconds)
                delay_seconds *= 2
            else:
                # Permanent failure or last retry exhausted
                logger.warning(f"Failed to extract ingredients after {max_retries} attempts: {e}")
                return None

    logger.warning(f"Ingredient extraction exhausted all {max_retries} retries")
    return None


def detect_ingredients_tool(image_data: str) -> dict:
    """Tool function for ingredient detection (can be registered as @tool).

    This function is called by Agno Agent when IMAGE_DETECTION_MODE="tool".
    It provides structured output for the agent to use in recipe recommendations.

    Args:
        image_data: Base64-encoded image string or image URL.

    Returns:
        Dict with detected ingredients, confidence scores, and description.

    Raises:
        ValueError: If image cannot be processed.
    """
    try:
        # Get image bytes (from base64 or URL)
        image_bytes = None
        if image_data.startswith(("http://", "https://")):
            # URL-based image
            image_bytes = fetch_image_bytes(image_data)
        else:
            # Assume base64 encoded
            import base64
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                logger.warning(f"Failed to decode base64 image: {e}")
                image_bytes = None

        if not image_bytes:
            raise ValueError("Could not retrieve image bytes from provided data")

        # Validate format and size
        if not validate_image_format(image_bytes):
            raise ValueError("Invalid image format. Only JPEG and PNG are supported.")

        if not validate_image_size(image_bytes):
            raise ValueError(f"Image too large. Maximum size is {config.MAX_IMAGE_SIZE_MB}MB")

        # Extract ingredients with retry logic
        result = extract_ingredients_with_retries(image_bytes)
        if not result:
            raise ValueError("Failed to extract ingredients from image. Please try another image.")

        # Filter by confidence
        ingredients = filter_ingredients_by_confidence(
            result.get("ingredients", []), result.get("confidence_scores", {})
        )

        if not ingredients:
            raise ValueError("No ingredients detected with sufficient confidence. Please try another image.")

        # Build description
        confidence_scores = result.get("confidence_scores", {})
        scores_text = ", ".join(
            f"{ing} ({confidence_scores.get(ing, 0):.0%})" for ing in ingredients[:5]
        )
        image_description = f"Detected ingredients: {scores_text}"
        if len(ingredients) > 5:
            image_description += f" and {len(ingredients) - 5} more"

        return {
            "ingredients": ingredients,
            "confidence_scores": {ing: confidence_scores.get(ing, 0) for ing in ingredients},
            "image_description": image_description,
        }

    except Exception as e:
        logger.error(f"Ingredient detection tool failed: {e}")
        raise ValueError(f"Ingredient detection failed: {str(e)}")
