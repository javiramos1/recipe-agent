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


# ============================================================================
# Error Handling Helpers
# ============================================================================


def _log_error(operation_name: str, exception: Exception, log_level: str = "warning") -> None:
    """Log error with appropriate level. Helper to reduce duplication.

    Args:
        operation_name: Description for logging
        exception: Exception that occurred
        log_level: Logging level ("debug", "warning", "error"). Default: "warning".
    """
    msg = f"{operation_name}: {exception}"
    if log_level == "debug":
        logger.debug(msg)
    elif log_level == "error":
        logger.error(msg)
    else:
        logger.warning(msg)


async def safe_execute_async(
    coro,
    operation_name: str,
    log_level: str = "warning",
    default_return=None,
    reraise: bool = False,
):
    """Safely execute async operation with consistent error logging.

    Consolidates try/except/log pattern for optional operations that should
    degrade gracefully. Typically used for operations where failure is not critical:
    - Image compression: Use original if compression fails
    - JSON parsing: Try alternative parsing method
    - Image fetching: Return None to allow retries

    Args:
        coro: Awaitable coroutine to execute.
        operation_name: Description for logging (e.g., "Fetch image from URL").
        log_level: Logging level ("debug", "warning", "error"). Default: "warning".
        default_return: Value to return on exception. Default: None (graceful degradation).
        reraise: If True, re-raise exception after logging (for critical ops). Default: False.

    Returns:
        Result of coroutine if successful.
        default_return on exception if reraise=False (suppresses exception).
        Raises original exception if reraise=True (preserves exception chain).

    Raises:
        Exception: Original exception if reraise=True.

    Example:
        # Graceful degradation (current default behavior):
        result = await safe_execute_async(compress_image(), "Compress", default_return=original_bytes)
        # Returns original_bytes if compress fails, continues execution

        # Critical operation (fail fast):
        result = await safe_execute_async(fetch_api(), "API call", reraise=True)
        # Raises exception if fetch fails, stops execution
    """
    try:
        return await coro
    except Exception as e:
        _log_error(operation_name, e, log_level)
        if reraise:
            raise  # Preserve original exception chain with 'raise' (not 'raise e')
        return default_return


def safe_execute_sync(
    func,
    operation_name: str,
    log_level: str = "warning",
    default_return=None,
    reraise: bool = False,
):
    """Safely execute sync operation with consistent error logging.

    Synchronous version of safe_execute_async. Same behavior and patterns.
    Used for operations where exception handling should be consistent across
    async and sync code paths.

    Args:
        func: Callable to execute (no args).
        operation_name: Description for logging.
        log_level: Logging level ("debug", "warning", "error"). Default: "warning".
        default_return: Value to return on exception. Default: None (graceful degradation).
        reraise: If True, re-raise exception after logging (for critical ops). Default: False.

    Returns:
        Result of func if successful.
        default_return on exception if reraise=False (suppresses exception).
        Raises original exception if reraise=True (preserves exception chain).

    Raises:
        Exception: Original exception if reraise=True.
    """
    try:
        return func()
    except Exception as e:
        _log_error(operation_name, e, log_level)
        if reraise:
            raise  # Preserve original exception chain with 'raise' (not 'raise e')
        return default_return


def compress_image(image_bytes: bytes, max_width: int = 1024) -> bytes:
    """Compress image for API transmission using Pillow.

    Uses JPEG format with quality=85 + optimize + progressive for optimal size/quality trade-off.
    Resizes oversized images and converts color modes to RGB.
    Only compresses if image size is below COMPRESS_IMG_THRESHOLD_KB.

    Args:
        image_bytes: Raw image bytes to compress
        max_width: Maximum image width in pixels

    Returns:
        Compressed image bytes (or original if PIL unavailable or size exceeds threshold)
    """
    if not HAS_PIL:
        logger.debug("PIL not available, skipping image compression")
        return image_bytes

    # Check if image size is below compression threshold (skip compression for large images)
    size_kb = len(image_bytes) / 1024
    logger.debug(f"Image size: {size_kb:.1f}KB, threshold: {config.COMPRESS_IMG_THRESHOLD_KB}KB")
    if size_kb < config.COMPRESS_IMG_THRESHOLD_KB:
        logger.debug(
            f"Image size {size_kb:.1f}KB below compression threshold "
            f"({config.COMPRESS_IMG_THRESHOLD_KB}KB), skipping compression"
        )
        return image_bytes

    def _compress():
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
            f"({(1 - compressed_size_mb / original_size_mb) * 100:.1f}% reduction)"
        )
        return compressed_bytes

    return safe_execute_sync(_compress, "Image compression", log_level="warning", default_return=image_bytes)


async def fetch_image_bytes(image_source: str | bytes) -> Optional[bytes]:
    """Fetch image bytes from URL or return directly if bytes.

    Handles multiple image source formats:
    - Direct bytes: Returned as-is
    - HTTP/HTTPS URLs: Fetched asynchronously (10s timeout)
    - Data URLs (data:image/jpeg;base64,...): Decoded from base64
    - Plain base64 strings: Decoded directly (see _get_image_bytes_from_source)

    Args:
        image_source: Either a URL string (http/https/data URI) or bytes object.

    Returns:
        Image bytes if fetch successful, None on any failure (logged as warning).

    Raises:
        None (exceptions logged, returns None for graceful degradation)

    Example:
        >>> image_bytes = await fetch_image_bytes("https://example.com/food.jpg")
        >>> # or
        >>> image_bytes = await fetch_image_bytes(b"\\xff\\xd8\\xff...")
    """
    if isinstance(image_source, bytes):
        return image_source

    if isinstance(image_source, str):
        # Handle data URLs (data:[<mediatype>][;base64],<data>)
        if image_source.startswith("data:"):

            def _decode_data_url():
                _, encoded = image_source.split(",", 1)
                return base64.b64decode(encoded)

            return safe_execute_sync(
                _decode_data_url,
                "Decode data URL",
                log_level="warning",
                default_return=None,
            )

        # Handle regular URLs
        async def _fetch_url():
            async with aiohttp.ClientSession() as session:
                async with session.get(image_source, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return await response.read()

        return await safe_execute_async(
            _fetch_url(),
            f"Fetch image from URL: {image_source}",
            log_level="warning",
            default_return=None,
        )

    return None


def validate_image_format(image_bytes: bytes) -> bool:
    """Validate image format (JPEG or PNG only).

    Uses filetype library to detect actual file format from magic bytes,
    not from extension. Supports: JPEG, JPG, PNG.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        True if valid format, False otherwise.

    Note:
        Returns False on any format other than JPEG/PNG. Caller responsible
        for checking return value and handling validation failure.
    """
    kind = filetype.guess(image_bytes)
    if kind is None or kind.extension not in ("jpg", "jpeg", "png"):
        logger.warning(f"Invalid image format: {kind}. Only JPEG and PNG supported.")
        return False
    return True


def validate_image_size(image_bytes: bytes) -> bool:
    """Validate image size against MAX_IMAGE_SIZE_MB.

    Checks raw byte length against configured size limit.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        True if size valid, False if exceeds limit.

    Note:
        Returns False if exceeded. Caller responsible for checking return
        value and handling size validation failure.
    """
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > config.MAX_IMAGE_SIZE_MB:
        logger.warning(f"Image size {size_mb:.2f}MB exceeds limit of {config.MAX_IMAGE_SIZE_MB}MB")
        return False
    return True


def parse_gemini_response(response_text: str) -> Optional[IngredientDetectionOutput]:
    """Parse JSON from Gemini response into validated IngredientDetectionOutput model.

    Implements lenient JSON parsing to handle Gemini responses that may include
    explanatory text before/after the JSON object. Tries multiple parsing strategies:
    1. Direct JSON.loads() on full response
    2. Regex extraction of JSON object from text
    3. Returns None if both fail

    Args:
        response_text: Raw response text from Gemini API (may include non-JSON text).

    Returns:
        Validated IngredientDetectionOutput instance if parsing and validation succeed.
        Returns None if:
        - No valid JSON found in response
        - JSON is malformed
        - Validation against IngredientDetectionOutput schema fails

    Note:
        Uses regex r'{.*}' to extract JSON, which works for single objects
        but may be fragile with nested structures or multiple objects.
    """

    def _parse_json_direct():
        return json.loads(response_text)

    def _parse_json_regex():
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None

    # Try direct JSON parse first
    parsed_dict = safe_execute_sync(
        _parse_json_direct,
        "Direct JSON parse",
        log_level="debug",
        default_return=None,
    )

    # Try regex extraction if direct parse failed
    if not parsed_dict:
        parsed_dict = safe_execute_sync(
            _parse_json_regex,
            "Regex JSON extraction",
            log_level="debug",
            default_return=None,
        )

    if not parsed_dict:
        logger.warning("Failed to parse JSON from Gemini response")
        return None

    # Validate and parse into IngredientDetectionOutput model
    def _validate_output():
        ingredients = parsed_dict.get("ingredients", [])
        confidence_scores = parsed_dict.get("confidence_scores", {})
        image_description = parsed_dict.get("image_description", None)

        return IngredientDetectionOutput(
            ingredients=ingredients,
            confidence_scores=confidence_scores,
            image_description=image_description,
        )

    return safe_execute_sync(
        _validate_output,
        "Validate IngredientDetectionOutput schema",
        log_level="warning",
        default_return=None,
    )


async def extract_ingredients_from_image(image_bytes: bytes) -> Optional[IngredientDetectionOutput]:
    """Call Gemini vision API to extract ingredients from image (single attempt, no retries).

    Makes a single API call to Gemini's vision model to analyze food images
    and extract ingredient information with confidence scores. Does NOT implement
    retry logic - that's handled by caller (extract_ingredients_with_retries).

    **API Contract:**
    - Input: Raw image bytes (JPEG or PNG, validated by caller)
    - Output: JSON with ingredients[] and confidence_scores{} dict
    - Format: Parsed and validated against IngredientDetectionOutput schema

    Args:
        image_bytes: Raw image bytes (must be JPEG or PNG format, validated by caller).

    Returns:
        Validated IngredientDetectionOutput with:
        - ingredients: List of detected ingredient names
        - confidence_scores: Dict mapping each ingredient to 0.0-1.0 confidence score
        - image_description: Optional human-readable description of detected items

        Returns None if:
        - Unable to determine image format (shouldn't happen if validated)
        - API call fails
        - Response parsing fails
        - Response validation fails

    Raises:
        None (exceptions logged as warnings, returns None for graceful degradation)

    Note:
        - Single attempt only (no retries here)
        - Assumes caller wraps with extract_ingredients_with_retries for retry logic
        - Uses asyncio.to_thread to call sync Gemini client in async context
    """

    async def _call_gemini_api():
        # Determine MIME type based on image format
        kind = filetype.guess(image_bytes)
        if kind is None:
            raise ValueError("Unable to determine image format")

        mime_type = "image/jpeg" if kind.extension in ("jpg", "jpeg") else "image/png"

        # Initialize Gemini client
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        # Call vision API with JSON response format
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.IMAGE_DETECTION_MODEL,
            contents=[
                'Extract all food ingredients from this image. Return ONLY valid JSON with \'ingredients\' list (strings) and \'confidence_scores\' dict mapping ingredient name to confidence (0.0-1.0). Example: {"ingredients": ["tomato", "basil"], "confidence_scores": {"tomato": 0.95, "basil": 0.88}}',
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )

        # Parse and validate response into IngredientDetectionOutput
        return parse_gemini_response(response.text)

    return await safe_execute_async(
        _call_gemini_api(),
        "Gemini vision API call",
        log_level="warning",
        default_return=None,
    )


def filter_ingredients_by_confidence(ingredients: list[str], confidence_scores: dict[str, float]) -> list[str]:
    """Filter ingredients by MIN_INGREDIENT_CONFIDENCE threshold.

    Removes ingredients that scored below the confidence threshold in the
    confidence_scores dict. Preserves order of remaining ingredients.

    Args:
        ingredients: List of ingredient names.
        confidence_scores: Dict mapping ingredient name to confidence score (0.0-1.0).

    Returns:
        Filtered list of ingredients with confidence >= MIN_INGREDIENT_CONFIDENCE threshold.
        Empty list [] if no ingredients meet threshold.

    Note:
        - Logs debug info if any ingredients were filtered out
        - Uses config.MIN_INGREDIENT_CONFIDENCE (default: 0.7)
        - Handles missing confidence scores by treating them as 0.0
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


async def prepare_and_extract_ingredients(
    image_bytes: bytes,
    with_retries: bool = True,
    image_idx: int = 0,
) -> Optional[tuple[list[str], IngredientDetectionOutput]]:
    """Unified pipeline: validate → compress → extract → filter ingredients.

    Consolidates the full image processing workflow into a single function
    used by both _process_single_image (no retries) and detect_ingredients_tool (with retries).

    **Pipeline Steps:**
    1. Validate image format (JPEG/PNG only)
    2. Validate image size (MAX_IMAGE_SIZE_MB limit)
    3. Optionally compress for API transmission
    4. Extract ingredients from image (with or without retries)
    5. Filter by confidence threshold (MIN_INGREDIENT_CONFIDENCE)

    Args:
        image_bytes: Raw image bytes to process.
        with_retries: Whether to use extract_ingredients_with_retries (True) or
                     extract_ingredients_from_image (False). Default: True.
        image_idx: Image index in batch (0-based) for logging context. Default: 0.

    Returns:
        Tuple of (filtered_ingredients_list, raw_IngredientDetectionOutput) on success.
        None if processing failed at any step (format/size validation, extraction).

    Raises:
        None (exceptions logged, returns None for graceful degradation)

    Side Effects:
        Logs progress and validation failures.
    """
    # Validate format
    if not validate_image_format(image_bytes):
        return None

    # Validate size
    if not validate_image_size(image_bytes):
        return None

    # Optionally compress
    if config.COMPRESS_IMG:
        logger.debug(f"Image {image_idx + 1}: Compressing for API transmission...")
        image_bytes = compress_image(image_bytes)

    # Extract ingredients (with or without retries)
    if with_retries:
        result = await extract_ingredients_with_retries(image_bytes)
    else:
        result = await extract_ingredients_from_image(image_bytes)

    if not result:
        logger.warning(f"Image {image_idx + 1}: Failed to extract ingredients")
        return None

    # Filter by confidence threshold
    ingredients = filter_ingredients_by_confidence(result.ingredients, result.confidence_scores)

    return (ingredients, result)


async def _get_image_bytes_from_source(image_source) -> Optional[bytes]:
    """Extract image bytes from various source formats.

    Unified source handler that abstracts away different image source types.
    Supports: string URLs, data URIs, plain base64, bytes, objects with url/content attributes.

    Args:
        image_source: Image source in any supported format:
            - str with URL scheme: URL or data URI (passed to fetch_image_bytes)
            - str plain base64: Decoded as base64 string
            - bytes: Raw image data (returned as-is)
            - object with .url: Extracted and passed to fetch_image_bytes
            - object with .content: Extracted and passed to fetch_image_bytes

    Returns:
        Image bytes or None if extraction/fetch failed.

    Note:
        - Used by _process_single_image and other batch processing
        - Returns None on any failure (logged by called functions)
        - Handles base64 decoding that was previously duplicated in detect_ingredients_tool
    """
    if isinstance(image_source, bytes):
        return image_source

    if isinstance(image_source, str):
        # Handle URL schemes (http, https, data) - delegate to fetch_image_bytes
        if image_source.startswith(("http://", "https://", "data:")):
            return await fetch_image_bytes(image_source)

        # Handle plain base64 string - decode directly
        def _decode_base64():
            return base64.b64decode(image_source)

        return safe_execute_sync(
            _decode_base64,
            "Decode base64 image string",
            log_level="warning",
            default_return=None,
        )

    # Handle objects with url or content attributes
    if hasattr(image_source, "url"):
        return await fetch_image_bytes(image_source.url)
    if hasattr(image_source, "content"):
        return await fetch_image_bytes(image_source.content)

    return None


async def _process_single_image(image_source, idx: int) -> Optional[list[str]]:
    """Process single image through complete validation and extraction pipeline.

    Orchestrates the full image processing workflow for one image using the unified
    prepare_and_extract_ingredients pipeline (without retries - used in pre-hook mode).

    Args:
        image_source: Image source (URL, bytes, or object with url/content attribute)
        idx: Image index in batch (0-based), used for logging context

    Returns:
        List of extracted ingredient names (post-filtering), or None if processing failed at any step.
        Empty list [] if extraction succeeds but no ingredients meet confidence threshold.

    Raises:
        None (all errors logged as warnings/info, returns None for graceful degradation)

    Side Effects:
        Logs progress at INFO level, warnings at WARNING/DEBUG levels
    """
    # Get image bytes from source
    image_bytes = await _get_image_bytes_from_source(image_source)
    if not image_bytes:
        logger.warning(f"Image {idx + 1}: Failed to get image bytes")
        return None

    # Use unified pipeline (without retries, since pre-hook has manual retries in extract_ingredients_pre_hook)
    result = await prepare_and_extract_ingredients(image_bytes, with_retries=False, image_idx=idx)
    if result is None:
        return None

    ingredients, _ = result

    if ingredients:
        logger.info(
            f"Image {idx + 1}: Extracted {len(ingredients)} ingredients "
            f"(confidence threshold: {config.MIN_INGREDIENT_CONFIDENCE})"
        )
        return ingredients

    logger.warning(f"Image {idx + 1}: No ingredients with sufficient confidence")
    return None


async def extract_ingredients_pre_hook(
    run_input,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """Pre-hook: Extract ingredients from images BEFORE agent processes request.

    **Critical Pattern**: This pre-hook runs BEFORE Agno agent processes user input.
    Pre-hooks do NOT have automatic retries (unlike tools or agent-level retries).
    Therefore, manual retry logic in extract_ingredients_with_retries is REQUIRED.

    **Processing Steps:**
    1. Extracts ChatMessage from RunInput (minimal input schema: message + optional images)
    2. Validates images are present (skips hook if no images)
    3. Processes all images in parallel for efficiency (asyncio.gather with _process_single_image)
    4. Deduplicates extracted ingredients while preserving order
    5. Appends detected ingredients to user message as text block: "[Detected Ingredients] ..."
    6. Clears images from ChatMessage (prevents large base64 data from being sent downstream to agent)
    7. Returns modified RunInput with enriched message

    **Example:**

    Input:
    ```python
    ChatMessage(
        message="What can I cook?",
        images=["data:image/jpeg;base64,/9j/...", "https://example.com/food.png"]
    )
    ```

    Output (enriched message):
    ```python
    ChatMessage(
        message="What can I cook?\\n\\n[Detected Ingredients] tomato, basil, mozzarella",
        images=[]  # Cleared
    )
    ```

    Args:
        run_input: Agno RunInput object containing ChatMessage data with images
        session: Agno AgentSession providing current session context (optional)
        user_id: User identifier for audit/logging context (optional, passed by Agno)
        debug_mode: Enable verbose debug logging (optional, passed by Agno)

    Returns:
        None (modifies run_input.input_content in-place per Agno pre-hook contract)

    Raises:
        None (pre-hooks must be resilient - catches all exceptions, logs warnings, clears images as fallback)

    Important:
        - This hook is CRITICAL: prevents large image data from being sent to Agno agent
        - Runs in parallel improves multi-image performance (asyncio.gather)
        - Confidence filtering (MIN_INGREDIENT_CONFIDENCE) happens here, before agent sees ingredients
        - Images are cleared REGARDLESS of extraction success (prevents data bloat)
        - Has manual retry logic in extract_ingredients_with_retries because pre-hooks don't get Agno retries
    """
    try:
        # Log pre-hook execution context
        session_id = getattr(session, "session_id", None) if session else None
        logger.info(
            f"Pre-hook: extract_ingredients_pre_hook(session_id={session_id}, "
            f"user_id={user_id}, debug_mode={debug_mode})"
        )

        # Extract ChatMessage data from RunInput
        input_data = getattr(run_input, "input_content", None)
        if not input_data or not hasattr(input_data, "message"):
            logger.debug("No valid ChatMessage found in RunInput")
            return

        message_text = input_data.message or ""
        images = input_data.images or []

        # Check if we have images to process
        if not images:
            logger.debug("No images in request, skipping ingredient extraction")
            return

        logger.debug(f"Found {len(images)} image(s), processing in parallel...")

        # Process all images in parallel for better performance
        tasks = [_process_single_image(image, idx) for idx, image in enumerate(images)]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Flatten and deduplicate ingredients from all images
        all_ingredients = []
        for result in results:
            if result:
                all_ingredients.extend(result)

        # Append detected ingredients to message if any were found
        if all_ingredients:
            unique_ingredients = list(dict.fromkeys(all_ingredients))  # Remove duplicates, preserve order
            ingredient_text = ", ".join(unique_ingredients)
            updated_message = f"{message_text}\n\n[Detected Ingredients] {ingredient_text}"

            # Update ChatMessage object's message field
            input_data.message = updated_message
            run_input.input_content = input_data

            logger.info(
                f"Ingredients extracted from image: {unique_ingredients} "
                f"(total: {len(unique_ingredients)}, confidence threshold: {config.MIN_INGREDIENT_CONFIDENCE})"
            )

        # Always clear images from the ChatMessage (whether extraction succeeded or failed)
        # This prevents large base64-encoded images from being sent to the agent after extraction
        input_data.images = []
        run_input.input_content = input_data
        logger.debug("Images cleared from request after ingredient extraction")

    except Exception as e:
        # Pre-hooks must be resilient - log but don't crash
        logger.warning(f"Ingredient extraction pre-hook failed: {e}")
        # Still clear images even on error to prevent them from being sent downstream
        try:
            input_data = getattr(run_input, "input_content", None)
            if input_data:
                input_data.images = []
                run_input.input_content = input_data
        except Exception as clear_error:
            logger.warning(f"Failed to clear images on error: {clear_error}")


async def extract_ingredients_with_retries(
    image_bytes: bytes, max_retries: int = 3
) -> Optional[IngredientDetectionOutput]:
    """Call Gemini vision API with exponential backoff retry logic (async).

    **CRITICAL**: This function implements MANUAL retry logic because:
    - Used in PRE-HOOK mode where Agno retries are NOT available
    - Pre-hooks cannot access agent-level exponential_backoff settings
    - Without this, transient API failures would break ingredient extraction
    - When used as tool, avoids extra LLM round-trips for retries

    Distinguishes between transient errors (network, timeouts, 429/5xx) and
    permanent errors (invalid API key, malformed request) to avoid futile retries.

    **Retry Strategy:**
    - Transient errors: Retry with exponential backoff (1s → 2s → 4s delays)
    - Permanent errors: Fail immediately without retry
    - No result (None from API): Treated as transient, retry
    - Last retry failure: Log and return None

    Args:
        image_bytes: Raw image bytes to process.
        max_retries: Maximum number of retry attempts (default: 3 = 1s + 2s + 4s = 7s max)

    Returns:
        Validated IngredientDetectionOutput on success.
        None if all retries exhausted (logged as warning).

    Raises:
        None (exceptions logged, returns None on final failure)

    Note:
        - Implements component-level retry (separate from agent-level retries)
        - Used for both pre-hook mode AND tool mode ingredient extraction
        - When used as tool: prevents extra LLM calls by handling retries here
        - Transient keyword detection: "timeout", "connection", "429", "500", "503", "502", "retryable"
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
                logger.debug(
                    f"Retrying ingredient extraction (attempt {retry_count + 1}/{max_retries}) after {delay_seconds}s"
                )
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2  # Exponential backoff
        except Exception as e:
            # Check if error is transient or permanent
            error_str = str(e).lower()
            is_transient = any(
                keyword in error_str for keyword in ["timeout", "connection", "429", "500", "503", "502", "retryable"]
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
    """Extract ingredients from image using Gemini vision API - @tool entry point.

    This is the main entry point for ingredient detection when used as a tool
    (IMAGE_DETECTION_MODE="tool"). The @tool decorator in agent.py wraps this function.

    **When Used:**
    - Agent can call this tool explicitly during reasoning
    - User asks for ingredient analysis on demand
    - Less efficient than pre-hook mode (extra agent reasoning turn)
    - More flexible - agent can choose when to call

    **Why Manual Retries Here Too:**
    When used as tool, includes extract_ingredients_with_retries() to avoid
    extra LLM round-trips. Agent sees a single tool call with retries
    handled internally, rather than agent retrying the tool call (which would
    be extra reasoning turns).

    **Processing:**
    1. Retrieves image bytes from URL, data URL, or base64 (via _get_image_bytes_from_source)
    2. Validates format (JPEG/PNG) and size constraints
    3. Optionally compresses for API transmission
    4. Extracts ingredients with exponential backoff retries
    5. Filters by confidence threshold
    6. Validates output against IngredientDetectionOutput schema

    Args:
        image_data: Image in any supported format:
            - "https://example.com/food.jpg" (HTTP/HTTPS URL)
            - "data:image/jpeg;base64,/9j/4AAQ..." (data URL with base64)
            - "iVBORw0KGgoAAAANSUhEUg..." (plain base64 string)

    Returns:
        IngredientDetectionOutput with validated:
        - ingredients: List of detected ingredient names (filtered by confidence)
        - confidence_scores: Dict mapping ingredients to 0.0-1.0 scores
        - image_description: Optional human-readable description of detected items

    Raises:
        ValueError: If image cannot be processed, with specific details:
        - "Could not retrieve image bytes from provided data" (base64/URL fetch failed)
        - "Invalid image format. Only JPEG and PNG are supported."
        - "Image too large. Maximum size is {MAX_IMAGE_SIZE_MB}MB"
        - "Failed to extract ingredients from image. Please try another image." (API/extraction failed after retries)
        - "No ingredients detected with sufficient confidence. Please try another image." (all filtered out)

    Important:
        - Raises ValueError for agent handling (structured error reporting)
        - Agno's agent-level retries will catch ValueError and decide to retry
        - Schema validation ensures response matches RecipeResponse expectations
        - Includes extract_ingredients_with_retries() to avoid extra LLM calls
    """
    try:
        # Get image bytes using unified source handler (handles URL, data URI, and base64)
        image_bytes = await _get_image_bytes_from_source(image_data)
        if not image_bytes:
            raise ValueError("Could not retrieve image bytes from provided data")

        # Explicit validation for tool mode to provide specific error messages
        if not validate_image_format(image_bytes):
            raise ValueError("Invalid image format. Only JPEG and PNG are supported.")

        if not validate_image_size(image_bytes):
            raise ValueError(f"Image too large. Maximum size is {config.MAX_IMAGE_SIZE_MB}MB")

        # Compress if enabled
        if config.COMPRESS_IMG:
            image_bytes = compress_image(image_bytes)

        # Extract ingredients with retries
        result = await extract_ingredients_with_retries(image_bytes)
        if result is None:
            raise ValueError("Failed to extract ingredients from image. Please try another image.")

        # Filter by confidence
        ingredients = filter_ingredients_by_confidence(result.ingredients, result.confidence_scores)
        if not ingredients:
            raise ValueError("No ingredients detected with sufficient confidence. Please try another image.")

        # Return validated IngredientDetectionOutput with filtered ingredients
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
        raise ValueError(f"Ingredient detection failed: {str(e)}") from e
