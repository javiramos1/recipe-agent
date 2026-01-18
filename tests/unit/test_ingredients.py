"""Unit tests for ingredient extraction pre-hook.

Tests cover:
- Image format validation (JPEG/PNG only)
- Image size validation
- JSON response parsing from Gemini API
- Confidence score filtering
- Error handling and resilience
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from ingredients import (
    detect_ingredients_tool,
    extract_ingredients_from_image,
    extract_ingredients_pre_hook,
    extract_ingredients_with_retries,
    filter_ingredients_by_confidence,
    parse_gemini_response,
    validate_image_format,
    validate_image_size,
)


class TestValidateImageFormat:
    """Test image format validation."""

    def test_valid_jpeg(self):
        """JPEG images should be valid."""
        # JPEG magic bytes: FF D8 FF
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        assert validate_image_format(jpeg_bytes) is True

    def test_valid_png(self):
        """PNG images should be valid."""
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        assert validate_image_format(png_bytes) is True

    def test_invalid_format(self):
        """Non-JPEG/PNG images should be rejected."""
        gif_bytes = b"GIF89a"  # GIF format
        assert validate_image_format(gif_bytes) is False

    def test_empty_bytes(self):
        """Empty bytes should be rejected."""
        assert validate_image_format(b"") is False


class TestValidateImageSize:
    """Test image size validation."""

    def test_valid_size(self):
        """Images within size limit should be valid."""
        # 1MB of data
        data = b"x" * (1024 * 1024)
        assert validate_image_size(data) is True

    def test_exactly_at_limit(self):
        """Images exactly at size limit should be valid."""
        # 5MB (default limit)
        data = b"x" * (5 * 1024 * 1024)
        assert validate_image_size(data) is True


class TestParseGeminiResponse:
    """Test JSON parsing from Gemini responses."""

    def test_valid_json(self):
        """Valid JSON should parse correctly."""
        response = '{"ingredients": ["tomato", "basil"], "confidence_scores": {"tomato": 0.95}}'
        result = parse_gemini_response(response)
        assert result is not None
        assert result["ingredients"] == ["tomato", "basil"]
        assert result["confidence_scores"]["tomato"] == 0.95

    def test_json_with_surrounding_text(self):
        """JSON with surrounding text should be extracted."""
        response = (
            "Here's the extracted ingredients:\n\n"
            '{"ingredients": ["tomato"], "confidence_scores": {"tomato": 0.9}}'
            "\n\nDone!"
        )
        result = parse_gemini_response(response)
        assert result is not None
        assert result["ingredients"] == ["tomato"]

    def test_invalid_json(self):
        """Invalid JSON should return None."""
        response = "This is not JSON at all"
        result = parse_gemini_response(response)
        assert result is None

    def test_malformed_json(self):
        """Malformed JSON should return None."""
        response = '{"ingredients": ["tomato", "basil"'  # Missing closing brace
        result = parse_gemini_response(response)
        assert result is None

    def test_empty_string(self):
        """Empty response should return None."""
        result = parse_gemini_response("")
        assert result is None


class TestFilterIngredientsByConfidence:
    """Test confidence-based ingredient filtering."""

    def test_all_above_threshold(self):
        """All ingredients above threshold (0.7) should be kept."""
        ingredients = ["tomato", "basil", "mozzarella"]
        confidence_scores = {"tomato": 0.95, "basil": 0.88, "mozzarella": 0.92}
        result = filter_ingredients_by_confidence(ingredients, confidence_scores)
        assert result == ingredients

    def test_some_below_threshold(self):
        """Ingredients below threshold (0.7) should be filtered out."""
        ingredients = ["tomato", "basil", "something"]
        confidence_scores = {"tomato": 0.95, "basil": 0.75, "something": 0.3}
        result = filter_ingredients_by_confidence(ingredients, confidence_scores)
        # Only tomato is >= 0.7
        assert "tomato" in result
        assert "something" not in result

    def test_missing_confidence_score(self):
        """Ingredients without confidence scores should be filtered out."""
        ingredients = ["tomato", "basil", "unknown"]
        confidence_scores = {"tomato": 0.95, "basil": 0.88}  # 'unknown' missing
        result = filter_ingredients_by_confidence(ingredients, confidence_scores)
        assert result == ["tomato", "basil"]

    def test_empty_ingredients(self):
        """Empty ingredient list should return empty list."""
        result = filter_ingredients_by_confidence([], {})
        assert result == []


class TestExtractIngredientsPreHook:
    """Test the main pre-hook function."""

    def test_no_images(self):
        """Request without images should return early."""
        run_input = Mock()
        run_input.images = []
        run_input.input_content = "What can I make?"

        extract_ingredients_pre_hook(run_input)

        # Should not modify input
        assert run_input.input_content == "What can I make?"
        assert run_input.images == []

    def test_no_images_attribute(self):
        """Request without images attribute should return early."""
        run_input = Mock(spec=[])  # No images attribute
        run_input.input_content = "What can I make?"

        # Should not crash
        extract_ingredients_pre_hook(run_input)

    @patch("ingredients.fetch_image_bytes")
    @patch("ingredients.extract_ingredients_from_image")
    def test_successful_extraction(self, mock_extract, mock_fetch):
        """Successful extraction should append ingredients to message."""
        # PNG magic bytes
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.return_value = {
            "ingredients": ["tomato", "basil"],
            "confidence_scores": {"tomato": 0.95, "basil": 0.88},
        }

        image = Mock()
        image.url = "http://example.com/image.jpg"

        run_input = Mock()
        run_input.images = [image]
        run_input.input_content = "What can I make?"

        extract_ingredients_pre_hook(run_input)

        # Should append ingredients
        assert "[Detected Ingredients]" in run_input.input_content
        assert "tomato" in run_input.input_content
        assert "basil" in run_input.input_content

        # Should clear images
        assert run_input.images == []

    @patch("ingredients.extract_ingredients_from_image")
    def test_failed_extraction(self, mock_extract):
        """Failed extraction should not modify message."""
        mock_extract.return_value = None

        image = Mock()
        image.url = "http://example.com/image.jpg"

        run_input = Mock()
        run_input.images = [image]
        run_input.input_content = "What can I make?"

        extract_ingredients_pre_hook(run_input)

        # Should not append ingredients
        assert "[Detected Ingredients]" not in run_input.input_content
        assert run_input.input_content == "What can I make?"

        # Should still clear images
        assert run_input.images == []

    @patch("ingredients.fetch_image_bytes")
    @patch("ingredients.extract_ingredients_from_image")
    def test_multiple_images(self, mock_extract, mock_fetch):
        """Multiple images should have ingredients combined."""
        # PNG magic bytes
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.side_effect = [
            {
                "ingredients": ["tomato", "basil"],
                "confidence_scores": {"tomato": 0.95, "basil": 0.88},
            },
            {
                "ingredients": ["mozzarella", "olive oil"],
                "confidence_scores": {"mozzarella": 0.92, "olive oil": 0.90},
            },
        ]

        image1 = Mock()
        image1.url = "http://example.com/image1.jpg"
        image2 = Mock()
        image2.url = "http://example.com/image2.jpg"

        run_input = Mock()
        run_input.images = [image1, image2]
        run_input.input_content = "What can I make?"

        extract_ingredients_pre_hook(run_input)

        # All ingredients should be present
        assert "tomato" in run_input.input_content
        assert "basil" in run_input.input_content
        assert "mozzarella" in run_input.input_content
        assert "olive oil" in run_input.input_content

    @patch("ingredients.fetch_image_bytes")
    @patch("ingredients.extract_ingredients_from_image")
    def test_duplicate_ingredients(self, mock_extract, mock_fetch):
        """Duplicate ingredients should be deduplicated."""
        # PNG magic bytes
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.side_effect = [
            {
                "ingredients": ["tomato", "basil"],
                "confidence_scores": {"tomato": 0.95, "basil": 0.88},
            },
            {
                "ingredients": ["tomato", "mozzarella"],  # 'tomato' again
                "confidence_scores": {"tomato": 0.93, "mozzarella": 0.92},
            },
        ]

        image1 = Mock()
        image1.url = "http://example.com/image1.jpg"
        image2 = Mock()
        image2.url = "http://example.com/image2.jpg"

        run_input = Mock()
        run_input.images = [image1, image2]
        run_input.input_content = "What can I make?"

        extract_ingredients_pre_hook(run_input)

        # Count occurrences of 'tomato' in ingredient text
        ingredients_section = run_input.input_content.split("[Detected Ingredients] ")[1]
        tomato_count = ingredients_section.count("tomato")

        # Should appear only once
        assert tomato_count == 1

    @patch("ingredients.extract_ingredients_from_image")
    def test_error_resilience(self, mock_extract):
        """Pre-hook should not crash on errors."""
        mock_extract.side_effect = Exception("API error")

        image = Mock()
        image.url = "http://example.com/image.jpg"

        run_input = Mock()
        run_input.images = [image]
        run_input.input_content = "What can I make?"

        # Should not raise exception
        extract_ingredients_pre_hook(run_input)

        # Should still clear images
        assert run_input.images == []


class TestExtractIngredientsFromImage:
    """Test the Gemini vision API integration."""

    @patch("ingredients.genai.Client")
    def test_successful_call(self, mock_client_class):
        """Successful API call should return parsed ingredients."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = '{"ingredients": ["tomato"], "confidence_scores": {"tomato": 0.95}}'
        mock_client.models.generate_content.return_value = mock_response

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_from_image(image_bytes)

        assert result is not None
        assert result["ingredients"] == ["tomato"]
        assert result["confidence_scores"]["tomato"] == 0.95

    @patch("ingredients.genai.Client")
    def test_invalid_response_structure(self, mock_client_class):
        """Invalid response structure should return None."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.text = '{"invalid": "structure"}'  # Missing required fields
        mock_client.models.generate_content.return_value = mock_response

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_from_image(image_bytes)

        assert result is None

    @patch("ingredients.genai.Client")
    def test_api_error(self, mock_client_class):
        """API errors should be caught and return None."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API error")

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_from_image(image_bytes)

        assert result is None


class TestExtractIngredientsWithRetries:
    """Test retry logic with exponential backoff."""

    @patch("ingredients.extract_ingredients_from_image")
    def test_success_first_attempt(self, mock_extract):
        """Should return immediately on first success."""
        mock_extract.return_value = {
            "ingredients": ["tomato"],
            "confidence_scores": {"tomato": 0.95},
        }

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_with_retries(image_bytes, max_retries=3)

        assert result is not None
        assert mock_extract.call_count == 1  # Only called once

    @patch("ingredients.extract_ingredients_from_image")
    @patch("time.sleep")
    def test_retry_on_transient_failure(self, mock_sleep, mock_extract):
        """Should retry on transient failures (network errors, timeouts)."""
        # First two calls fail with transient error, third succeeds
        mock_extract.side_effect = [
            Exception("Connection timeout"),
            Exception("503 Service Unavailable"),
            {
                "ingredients": ["tomato"],
                "confidence_scores": {"tomato": 0.95},
            },
        ]

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_with_retries(image_bytes, max_retries=3)

        assert result is not None
        assert mock_extract.call_count == 3  # Called 3 times (2 failures + 1 success)

    @patch("ingredients.extract_ingredients_from_image")
    @patch("time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_extract):
        """Should use exponential backoff (1s, 2s, 4s)."""
        mock_extract.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            Exception("Connection timeout"),
        ]

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_with_retries(image_bytes, max_retries=3)

        assert result is None
        # Should sleep twice (between attempts): 1s and 2s
        assert mock_sleep.call_count == 2
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls == [1, 2]

    @patch("ingredients.extract_ingredients_from_image")
    def test_no_retry_on_permanent_failure(self, mock_extract):
        """Should NOT retry on permanent failures (invalid API key)."""
        mock_extract.side_effect = Exception("Invalid API key")

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_with_retries(image_bytes, max_retries=3)

        assert result is None
        # Should be called only once (no retries on permanent error)
        assert mock_extract.call_count == 1

    @patch("ingredients.extract_ingredients_from_image")
    def test_max_retries_exceeded(self, mock_extract):
        """Should return None after max retries exceeded."""
        mock_extract.return_value = None  # Keeps returning None

        # PNG magic bytes
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        result = extract_ingredients_with_retries(image_bytes, max_retries=2)

        assert result is None
        assert mock_extract.call_count == 2  # Called exactly max_retries times


class TestDetectIngredientsTool:
    """Test the ingredient detection tool function."""

    @patch("ingredients.extract_ingredients_with_retries")
    @patch("ingredients.fetch_image_bytes")
    def test_successful_url_extraction(self, mock_fetch, mock_extract):
        """URL-based extraction should work correctly."""
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.return_value = {
            "ingredients": ["tomato", "basil"],
            "confidence_scores": {"tomato": 0.95, "basil": 0.88},
        }

        result = detect_ingredients_tool("http://example.com/image.jpg")

        assert result is not None
        assert result["ingredients"] == ["tomato", "basil"]
        assert "tomato" in result["confidence_scores"]
        assert "image_description" in result

    @patch("ingredients.extract_ingredients_with_retries")
    def test_successful_base64_extraction(self, mock_extract):
        """Base64-based extraction should work correctly."""
        import base64

        # PNG magic bytes in base64
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        image_base64 = base64.b64encode(png_bytes).decode()

        mock_extract.return_value = {
            "ingredients": ["tomato"],
            "confidence_scores": {"tomato": 0.95},
        }

        result = detect_ingredients_tool(image_base64)

        assert result is not None
        assert result["ingredients"] == ["tomato"]

    @patch("ingredients.fetch_image_bytes")
    def test_invalid_image_format(self, mock_fetch):
        """Invalid image format should raise ValueError."""
        mock_fetch.return_value = b"GIF89a"  # GIF format

        with pytest.raises(ValueError, match="Invalid image format"):
            detect_ingredients_tool("http://example.com/image.gif")

    @patch("ingredients.extract_ingredients_with_retries")
    @patch("ingredients.fetch_image_bytes")
    def test_no_ingredients_detected(self, mock_fetch, mock_extract):
        """No ingredients with sufficient confidence should raise ValueError."""
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.return_value = {
            "ingredients": [],  # Empty after filtering
            "confidence_scores": {},
        }

        with pytest.raises(ValueError, match="No ingredients detected"):
            detect_ingredients_tool("http://example.com/image.jpg")

    @patch("ingredients.fetch_image_bytes")
    def test_failed_to_fetch_image(self, mock_fetch):
        """Failed image fetch should raise ValueError."""
        mock_fetch.return_value = None

        with pytest.raises(ValueError, match="Could not retrieve image"):
            detect_ingredients_tool("http://example.com/image.jpg")

    @patch("ingredients.extract_ingredients_with_retries")
    @patch("ingredients.fetch_image_bytes")
    def test_image_description_multiple_ingredients(self, mock_fetch, mock_extract):
        """Image description should show confidence percentages."""
        mock_fetch.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_extract.return_value = {
            "ingredients": ["tomato", "basil", "mozzarella", "olive oil", "garlic", "extra"],
            "confidence_scores": {
                "tomato": 0.95,
                "basil": 0.88,
                "mozzarella": 0.92,
                "olive oil": 0.90,
                "garlic": 0.85,
                "extra": 0.75,
            },
        }

        result = detect_ingredients_tool("http://example.com/image.jpg")

        # Should show first 5 ingredients and mention "1 more"
        assert "1 more" in result["image_description"]
        assert "tomato" in result["image_description"]
        assert "95%" in result["image_description"]

