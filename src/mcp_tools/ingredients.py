"""Ingredient extraction from images using Gemini vision API.

This module provides two ways to extract ingredients from uploaded images:

1. PRE-HOOK MODE (default, IMAGE_DETECTION_MODE="pre-hook"):
   - extract_ingredients_pre_hook() runs BEFORE agent processes request
   - Extracts ingredients from images using Gemini vision API
   - Appends detected ingredients to user message as clean text
   - Clears images from input to prevent re-processing
   - Usage: Automatically registered in agent initialization

2. TOOL MODE (IMAGE_DETECTION_MODE="tool"):
   - detect_ingredients_tool() provides core extraction logic
   - Wrapped by @tool-decorated detect_image_ingredients() in agent.py
   - Agent calls tool when needed, has full visibility
   - Returns structured IngredientDetectionOutput
   - Usage: Automatically registered in agent initialization

Core Functions:
- fetch_image_bytes(): Get image bytes from URL or directly (async)
- validate_image_format(): Check JPEG/PNG only
- validate_image_size(): Check MAX_IMAGE_SIZE_MB limit
- parse_gemini_response(): Lenient JSON parsing
- extract_ingredients_from_image(): Call Gemini vision API (async)
- filter_ingredients_by_confidence(): Apply MIN_INGREDIENT_CONFIDENCE threshold
- extract_ingredients_with_retries(): Exponential backoff retry wrapper (async)
- detect_ingredients_tool(): Core ingredient extraction function (wrapped by @tool in agent.py)
"""

import asyncio
import base64
import json
import re
from io import BytesIO
from typing import Optional

import aiohttp
import filetype
from google import genai
from google.genai import types

from src.utils.config import config
from src.utils.logger import logger
from src.models.models import IngredientDetectionOutput

# Try to import PIL for image compression
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def compress_image(image_bytes: bytes, max_width: int = 1024) -> bytes:
    """Compress image for API transmission using Pillow.
    
    Uses JPEG format with quality=85 + optimize + progressive for optimal size/quality trade-off.
    Resizes oversized images and converts color modes to RGB.
    
    Args:
        image_bytes: Raw image bytes to compress
        max_width: Maximum image width in pixels
        
    Returns:
        Compressed image bytes (or original if PIL unavailable)
    """
    if not HAS_PIL:
        logger.debug("PIL not available, skipping image compression")
        return image_bytes
    
    try:
        img = Image.open(BytesIO(image_bytes))
        original_size_mb = len(image_bytes) / (1024 * 1024)
        
        # Convert RGBA/LA/P to RGB for better compression
        if img.mode in ("RGBA", "LA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[-1])
            else:
                rgb_img.paste(img)
            img = rgb_img
        
        # Resize if oversized
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Compress to JPEG with quality 85 + optimize + progressive
        output = BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True, progressive=True)
        output.seek(0)
        compressed_bytes = output.read()
        compressed_size_mb = len(compressed_bytes) / (1024 * 1024)
        
        logger.debug(
            f"Image compressed: {original_size_mb:.2f}MB → {compressed_size_mb:.2f}MB "
            f"({(1 - compressed_size_mb/original_size_mb)*100:.1f}% reduction)"
        )
        return compressed_bytes
        
    except Exception as e:
        logger.warning(f"Failed to compress image: {e}. Using original.")
        return image_bytes


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

    Works with ChatMessage input schema:
    - run_input.message: User message (str)
    - run_input.images: List of image URLs or base64 data URIs (parsed by validator)

    The function:
    1. Extracts message and images from ChatMessage
    2. Validates and compresses images
    3. Calls Gemini vision API to extract ingredients (async)
    4. Filters by confidence threshold
    5. Appends detected ingredients to user message as text

    Args:
        run_input: Agno RunInput object with ChatMessage attributes (message, images)
        session: Agno AgentSession providing current session context
        user_id: Optional contextual user ID for the current run
        debug_mode: Optional boolean indicating if debug mode is enabled

    Returns:
        None (modifies run_input in-place)
    """
    try:
        # Log pre-hook execution context
        session_id = getattr(session, "session_id", None) if session else None
        logger.info(
            f"Pre-hook: extract_ingredients_pre_hook(session_id={session_id}, "
            f"user_id={user_id}, debug_mode={debug_mode})"
        )

        # Extract normalized message and images (validator parses comma-separated string to list)
        message_text = getattr(run_input, "message", "") or ""
        images = getattr(run_input, "images", []) or []
        
        logger.debug(f"Message: {len(message_text)} chars, Images: {len(images)} items")
        
        # Check if we have images to process
        if not images:
            logger.debug("No images in request, skipping ingredient extraction")
            return

        logger.debug(f"Found {len(images)} image(s), extracting ingredients...")

        all_ingredients = []
        for idx, image in enumerate(images):
            # Get image bytes from data URL or URL string (async)
            image_bytes = None
            if isinstance(image, str):
                image_bytes = await fetch_image_bytes(image)
            elif hasattr(image, "url"):
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
            
            # Compress image for API transmission (if enabled)
            if config.COMPRESS_IMG:
                logger.debug(f"Image {idx + 1}: Compressing for API transmission...")
                image_bytes = compress_image(image_bytes)

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
            # Update the message with detected ingredients
            run_input.input_content = (
                f"{message_text}\n\n[Detected Ingredients] {ingredient_text}"
            )
            logger.info(
                f"Ingredients extracted from image: {unique_ingredients} "
                f"(total: {len(unique_ingredients)})"
            )

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
    """Extract ingredients from image using Gemini vision API.
    
    Core implementation function called by the @tool-decorated wrapper in agent.py.
    Handles image validation, API calls, and confidence filtering.
    
    Args:
        image_data: Base64-encoded image string or URL.
    
    Returns:
        IngredientDetectionOutput with detected ingredients and confidence scores.
    
    Raises:
        ValueError: If image cannot be processed.
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
