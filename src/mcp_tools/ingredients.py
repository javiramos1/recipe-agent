"""Ingredient extraction from images using Gemini vision API.

This module provides two ways to extract ingredients from uploaded images:

1. PRE-HOOK MODE (default, IMAGE_DETECTION_MODE="pre-hook"):
   - extract_ingredients_pre_hook() runs BEFORE agent processes request
   - Extracts ingredients from images using Gemini vision API
   - Appends detected ingredients to user message as clean text: "[Detected Ingredients] ..."
   - Clears images from input to prevent re-processing
   - Handles errors gracefully without crashing
   - Usage: agent.add_pre_hook(extract_ingredients_pre_hook)

2. TOOL MODE (IMAGE_DETECTION_MODE="tool"):
   - detect_ingredients_tool() registered as Agno @tool
   - Agent calls tool when needed, has full visibility
   - Returns structured dict: {"ingredients": [...], "confidence_scores": {...}, "image_description": "..."}
   - Agent can ask clarifying questions about detected ingredients
   - Usage: @tool
           def detect_image_ingredients(image_data: str) -> dict:
               return detect_ingredients_tool(image_data)
           agent.add_tool(detect_image_ingredients)

Both modes use the same core functions:
- fetch_image_bytes(): Get image bytes from URL or directly (async)
- validate_image_format(): Check JPEG/PNG only
- validate_image_size(): Check MAX_IMAGE_SIZE_MB limit
- parse_gemini_response(): Lenient JSON parsing
- extract_ingredients_from_image(): Call Gemini vision API (async)
- filter_ingredients_by_confidence(): Apply MIN_INGREDIENT_CONFIDENCE threshold
- extract_ingredients_with_retries(): Exponential backoff retry wrapper (async)
"""

import asyncio
import base64
import json
import re
from typing import Optional

import aiohttp
import filetype
from google import genai
from google.genai import types

from src.utils.config import config
from src.utils.logger import logger
from src.models.models import IngredientDetectionOutput


async def fetch_image_bytes(image_source: str | bytes) -> Optional[bytes]:
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
            async with aiohttp.ClientSession() as session:
                async with session.get(image_source, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return await response.read()
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


def parse_gemini_response(response_text: str) -> Optional[IngredientDetectionOutput]:
    """Parse JSON from Gemini response into validated IngredientDetectionOutput model.
    
    Handles text before/after JSON and validates parsed data against IngredientDetectionOutput schema.

    Args:
        response_text: Raw response text from Gemini API.

    Returns:
        Validated IngredientDetectionOutput instance, or None on parse/validation failure.
    """
    parsed_dict = None
    
    try:
        # Try direct JSON parse first
        parsed_dict = json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text (Gemini might add explanatory text)
    if not parsed_dict:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            try:
                parsed_dict = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

    if not parsed_dict:
        logger.warning("Failed to parse JSON from Gemini response")
        return None

    # Validate and parse into IngredientDetectionOutput model
    try:
        # Extract fields with defaults for missing optional fields
        ingredients = parsed_dict.get("ingredients", [])
        confidence_scores = parsed_dict.get("confidence_scores", {})
        image_description = parsed_dict.get("image_description", None)
        
        # Create validated model instance
        output = IngredientDetectionOutput(
            ingredients=ingredients,
            confidence_scores=confidence_scores,
            image_description=image_description,
        )
        return output
    except Exception as e:
        logger.warning(f"Failed to validate parsed response against IngredientDetectionOutput: {e}")
        return None


async def extract_ingredients_from_image(image_bytes: bytes) -> Optional[IngredientDetectionOutput]:
    """Call Gemini vision API to extract ingredients from image.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        Validated IngredientDetectionOutput instance, or None on failure.
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
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.GEMINI_MODEL,
            contents=[
                "Extract all food ingredients from this image. Return ONLY valid JSON with 'ingredients' list (strings) and 'confidence_scores' dict mapping ingredient name to confidence (0.0-1.0). Example: {\"ingredients\": [\"tomato\", \"basil\"], \"confidence_scores\": {\"tomato\": 0.95, \"basil\": 0.88}}",
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )

        # Parse and validate response into IngredientDetectionOutput
        result = parse_gemini_response(response.text)
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


async def extract_ingredients_pre_hook(
    run_input,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """Pre-hook: Extract ingredients from images before agent processes request.

    This function:
    1. Checks for images in the request
    2. Calls Gemini vision API to extract ingredients (async)
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
            # Get image bytes (async)
            image_bytes = None
            if hasattr(image, "url"):
                image_bytes = await fetch_image_bytes(image.url)
            elif hasattr(image, "content"):
                image_bytes = await fetch_image_bytes(image.content)

            if not image_bytes:
                logger.warning(f"Image {idx + 1}: Failed to get image bytes")
                continue

            # Validate image
            if not validate_image_format(image_bytes):
                continue

            if not validate_image_size(image_bytes):
                continue

            # Extract ingredients from image (async) - returns validated IngredientDetectionOutput
            result = await extract_ingredients_from_image(image_bytes)
            if not result:
                logger.warning(f"Image {idx + 1}: Failed to extract ingredients")
                continue

            # Filter by confidence and extract ingredient names
            ingredients = filter_ingredients_by_confidence(
                result.ingredients, result.confidence_scores
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


async def extract_ingredients_with_retries(
    image_bytes: bytes, max_retries: int = 3
) -> Optional[IngredientDetectionOutput]:
    """Call Gemini vision API with exponential backoff retry logic (async).

    Retries on transient failures (network errors, rate limits, 5xx errors).
    Does NOT retry on permanent failures (invalid API key, malformed request).

    Args:
        image_bytes: Raw image bytes to process.
        max_retries: Maximum number of retry attempts (default: 3).

    Returns:
        Validated IngredientDetectionOutput instance, or None if all retries failed.
    """
    retry_count = 0
    delay_seconds = 1

    while retry_count < max_retries:
        try:
            result = await extract_ingredients_from_image(image_bytes)
            if result:
                return result
            # If result is None but no exception, retry (might be transient API issue)
            retry_count += 1
            if retry_count < max_retries:
                logger.debug(f"Retrying ingredient extraction (attempt {retry_count + 1}/{max_retries}) after {delay_seconds}s")
                await asyncio.sleep(delay_seconds)
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
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2
            else:
                # Permanent failure or last retry exhausted
                logger.warning(f"Failed to extract ingredients after {max_retries} attempts: {e}")
                return None

    logger.warning(f"Ingredient extraction exhausted all {max_retries} retries")
    return None


async def detect_ingredients_tool(image_data: str) -> IngredientDetectionOutput:
    """Tool function for ingredient detection (register with @tool decorator).

    This function extracts ingredients from uploaded images using Gemini vision API.
    It's designed to be registered as an Agno @tool when IMAGE_DETECTION_MODE="tool".

    IMPORTANT: This function is NOT a @tool decorator itself. It must be wrapped
    with @tool decorator in app.py for Agno agent registration.

    Function Behavior
    =================
    1. Accepts image_data as Base64 string or URL
    2. Validates image format (JPEG/PNG only) and size
    3. Calls Gemini vision API to extract ingredients (async)
    4. Filters results by MIN_INGREDIENT_CONFIDENCE threshold
    5. Returns structured IngredientDetectionOutput or raises ValueError

    Error Handling
    ==============
    Raises ValueError (not caught) so agent can handle errors:
    - Invalid image format → ValueError with explanation
    - Image too large → ValueError with size limit
    - No ingredients detected → ValueError with suggestion
    - Gemini API failure → ValueError with error details

    Args:
        image_data: Base64-encoded image string or image URL.
                   Examples:
                   - "https://example.com/image.jpg" (URL)
                   - "iVBORw0KGgoAAAANSUhEUg..." (Base64)

    Returns:
        IngredientDetectionOutput with validated fields:
        - ingredients: List[str] - ingredient names in order of confidence
        - confidence_scores: Dict[str, float] - name → confidence (0.0 < score < 1.0)
        - image_description: str - human-readable summary

        Example:
        IngredientDetectionOutput(
            ingredients=["tomato", "basil", "mozzarella"],
            confidence_scores={"tomato": 0.95, "basil": 0.88, "mozzarella": 0.82},
            image_description="Detected ingredients: tomato (95%), basil (88%), mozzarella (82%)"
        )

    Raises:
        ValueError: If image cannot be processed with details about the failure.

    """
    try:
        # Get image bytes (from base64 or URL) - async
        image_bytes = None
        if image_data.startswith(("http://", "https://")):
            # URL-based image
            image_bytes = await fetch_image_bytes(image_data)
        else:
            # Assume base64 encoded
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

        # Extract ingredients with retry logic (async) - returns validated IngredientDetectionOutput
        result = await extract_ingredients_with_retries(image_bytes)
        if not result:
            raise ValueError("Failed to extract ingredients from image. Please try another image.")

        # Filter by confidence to ensure we only return high-confidence ingredients
        ingredients = filter_ingredients_by_confidence(
            result.ingredients, result.confidence_scores
        )

        if not ingredients:
            raise ValueError("No ingredients detected with sufficient confidence. Please try another image.")

        # Return validated IngredientDetectionOutput with filtered ingredients
        # The model is already validated by parse_gemini_response(), just update if needed
        return IngredientDetectionOutput(
            ingredients=ingredients,
            confidence_scores={ing: result.confidence_scores[ing] for ing in ingredients},
            image_description=result.image_description,
        )

    except ValueError:
        # Re-raise ValueError (intended for agent handling)
        raise
    except Exception as e:
        logger.error(f"Ingredient detection tool failed: {e}")
        raise ValueError(f"Ingredient detection failed: {str(e)}")
