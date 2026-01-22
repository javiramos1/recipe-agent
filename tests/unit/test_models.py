"""Unit tests for Pydantic models validation."""

import json
import pytest
from pydantic import ValidationError

from src.models.models import (
    ChatMessage,
    Recipe,
    RecipeResponse,
    IngredientDetectionOutput,
)


class TestChatMessage:
    """Test ChatMessage model validation (minimal input schema)."""

    def test_valid_message_required_field_only(self):
        """Test valid message with only required message field."""
        msg = ChatMessage(message="Show me vegetarian recipes")
        assert msg.message == "Show me vegetarian recipes"
        assert msg.images is None

    def test_valid_message_with_images(self):
        """Test valid message with images."""
        images = ["data:image/jpeg;base64,/9j/4AAQSkZ...", "https://example.com/image.png"]
        msg = ChatMessage(message="What can I make with these?", images=images)
        assert msg.message == "What can I make with these?"
        assert msg.images == images

    def test_valid_message_with_empty_images_list(self):
        """Test valid message with empty images list."""
        msg = ChatMessage(message="Show recipes", images=[])
        assert msg.message == "Show recipes"
        assert msg.images == []

    def test_invalid_missing_message(self):
        """Test that neither message nor images is acceptable - auto-default sets message when images present."""
        # When images are provided, message auto-defaults
        msg = ChatMessage(images=["https://example.com/image.jpg"])
        assert msg.message == "What can I cook with these ingredients?"
        assert msg.images == ["https://example.com/image.jpg"]
        
        # When BOTH are missing, should raise error
        with pytest.raises(ValidationError) as exc:
            ChatMessage(message=None, images=None)
        assert "Either message or images" in str(exc.value)

    def test_invalid_empty_message(self):
        """Test invalid message with empty string."""
        with pytest.raises(ValidationError) as exc:
            ChatMessage(message="")
        assert "message" in str(exc.value)

    def test_valid_message_whitespace_stripped(self):
        """Test message with surrounding whitespace gets stripped."""
        msg = ChatMessage(message="  Show me recipes  ")
        assert msg.message == "Show me recipes"

    def test_valid_message_long_text(self):
        """Test message with maximum length (2000 chars)."""
        long_msg = "x" * 2000
        msg = ChatMessage(message=long_msg)
        assert msg.message == long_msg

    def test_invalid_message_too_long(self):
        """Test message exceeding maximum length."""
        long_msg = "x" * 2001
        with pytest.raises(ValidationError) as exc:
            ChatMessage(message=long_msg)
        assert "message" in str(exc.value)

    def test_valid_message_max_images(self):
        """Test message with maximum number of images (10)."""
        # Use valid image URLs for testing
        images = [f"https://example.com/image_{i}.jpg" for i in range(10)]
        msg = ChatMessage(message="Show me", images=images)
        assert len(msg.images) == 10

    def test_invalid_message_too_many_images(self):
        """Test message with too many images (>10)."""
        images = [f"image_{i}" for i in range(11)]
        with pytest.raises(ValidationError) as exc:
            ChatMessage(message="Show me", images=images)
        assert "images" in str(exc.value)

    def test_json_serialization_roundtrip(self):
        """Test ChatMessage can be serialized and deserialized."""
        original = ChatMessage(message="Test", images=["https://example.com/img1.jpg", "https://example.com/img2.jpg"])
        json_str = original.model_dump_json()
        restored = ChatMessage.model_validate_json(json_str)
        assert restored.message == original.message
        assert restored.images == original.images


class TestRecipe:
    """Test Recipe model validation."""

    def test_valid_recipe_all_fields(self):
        """Test valid recipe with all fields populated."""
        recipe = Recipe(
            id=12345,
            title="Tomato Pasta",
            summary="Classic Italian pasta with fresh tomatoes",
            ingredients=["pasta", "tomato", "garlic", "olive oil"],
            instructions=["Boil water", "Cook pasta", "Make sauce", "Combine"],
            ready_in_minutes=30,
            servings=4,
            source_url="https://example.com/recipe",
        )
        assert recipe.id == 12345
        assert recipe.title == "Tomato Pasta"
        assert recipe.summary == "Classic Italian pasta with fresh tomatoes"
        assert len(recipe.ingredients) == 4
        assert len(recipe.instructions) == 4
        assert recipe.ready_in_minutes == 30
        assert recipe.servings == 4
        assert recipe.source_url == "https://example.com/recipe"

    def test_valid_recipe_required_fields_only(self):
        """Test valid recipe with only required fields."""
        recipe = Recipe(
            id=54321,
            title="Simple Salad",
        )
        assert recipe.id == 54321
        assert recipe.title == "Simple Salad"
        assert recipe.summary is None
        assert recipe.source_url is None

    def test_valid_recipe_optional_fields_as_none(self):
        """Test recipe with explicitly set None for optional fields."""
        recipe = Recipe(
            id=99999,
            title="Breakfast",
            summary=None,
            source_url=None,
        )
        assert recipe.summary is None
        assert recipe.source_url is None

    def test_invalid_missing_title(self):
        """Test that missing title raises error."""
        with pytest.raises(ValidationError):
            Recipe(
                ingredients=["test"],
                instructions=["test"],
                prep_time_min=0,
                cook_time_min=0,
            )

    def test_valid_prep_time_string_coercion(self):
        """Test that ready_in_minutes as string is coerced to int by Pydantic."""
        recipe = Recipe(
            id=111,
            title="Test",
            ready_in_minutes="30",
        )
        assert recipe.ready_in_minutes == 30
        assert isinstance(recipe.ready_in_minutes, int)

    def test_valid_cook_time_string_coercion(self):
        """Test that ready_in_minutes as string is coerced to int by Pydantic."""
        recipe = Recipe(
            id=222,
            title="Test",
            ready_in_minutes="45",
        )
        assert recipe.ready_in_minutes == 45
        assert isinstance(recipe.ready_in_minutes, int)


class TestRecipeResponse:
    """Test RecipeResponse model validation."""

    def test_valid_response_with_recipes(self):
        """Test valid response with recipes and metadata."""
        recipe = Recipe(
            id=333,
            title="Test Recipe",
            ready_in_minutes=15,
        )
        response = RecipeResponse(
            response="Here are some recipes for you.",
            recipes=[recipe],
            ingredients=["ingredient1", "ingredient2"],
            preferences=["vegetarian", "italian"],
            session_id="session123",
            run_id="run456",
            execution_time_ms=1500,
        )
        assert len(response.recipes) == 1
        assert response.recipes[0].title == "Test Recipe"
        assert response.session_id == "session123"
        assert response.execution_time_ms == 1500
        assert response.response == "Here are some recipes for you."

    def test_valid_response_with_optional_fields_none(self):
        """Test valid response with optional fields as None."""
        recipe = Recipe(
            id=444,
            title="Test",
        )
        response = RecipeResponse(
            response="Here's a test recipe.",
            recipes=[recipe],
            ingredients=["test"],
            preferences=[],
            session_id=None,
            run_id=None,
            execution_time_ms=100,
        )
        assert response.session_id is None
        assert response.run_id is None
        assert response.response == "Here's a test recipe."

    def test_valid_response_empty_recipes_list(self):
        """Test valid response with empty recipes list."""
        response = RecipeResponse(
            response="No recipes found for your request.",
            recipes=[],
            ingredients=[],
            preferences=[],
            execution_time_ms=50,
        )
        assert response.recipes == []
        assert response.ingredients == []
        assert response.response == "No recipes found for your request."

    def test_valid_response_multiple_recipes(self):
        """Test valid response with multiple recipes."""
        recipes = [
            Recipe(
                id=555 + i,
                title=f"Recipe {i}",
                ready_in_minutes=10 + i * 5,
            )
            for i in range(3)
        ]
        response = RecipeResponse(
            response="Found 3 great recipes for you!",
            recipes=recipes,
            ingredients=["ing1", "ing2", "ing3"],
            preferences=["keto"],
            execution_time_ms=2000,
        )
        assert len(response.recipes) == 3
        assert response.response == "Found 3 great recipes for you!"

    def test_invalid_missing_execution_time(self):
        """Test that missing execution_time_ms raises error."""
        with pytest.raises(ValidationError):
            RecipeResponse(
                recipes=[],
                ingredients=[],
                preferences={},
            )

    def test_valid_execution_time_string_coercion(self):
        """Test that execution_time_ms as string is coerced to int by Pydantic."""
        response = RecipeResponse(
            response="Test response.",
            recipes=[],
            ingredients=[],
            preferences=[],
            execution_time_ms="1500",
        )
        assert response.execution_time_ms == 1500
        assert isinstance(response.execution_time_ms, int)

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization and deserialization roundtrip."""
        recipe = Recipe(
            id=666,
            title="Roundtrip Test",
            ready_in_minutes=15,
        )
        original = RecipeResponse(
            response="Roundtrip test response.",
            recipes=[recipe],
            ingredients=["test"],
            preferences=["vegan"],
            execution_time_ms=1000,
        )
        json_str = original.model_dump_json()
        deserialized = RecipeResponse.model_validate_json(json_str)
        assert len(deserialized.recipes) == 1
        assert deserialized.recipes[0].title == "Roundtrip Test"
        assert deserialized.execution_time_ms == 1000
        assert deserialized.response == "Roundtrip test response."


class TestIngredientDetectionOutput:
    """Test IngredientDetectionOutput model validation."""

    def test_valid_output_with_all_fields(self):
        """Test valid output with all fields populated."""
        output = IngredientDetectionOutput(
            ingredients=["tomato", "garlic", "basil"],
            confidence_scores={
                "tomato": 0.95,
                "garlic": 0.88,
                "basil": 0.92,
            },
            image_description="Fresh vegetables on a wooden board",
        )
        assert len(output.ingredients) == 3
        assert output.confidence_scores["tomato"] == 0.95
        assert output.image_description == "Fresh vegetables on a wooden board"

    def test_valid_output_required_fields_only(self):
        """Test valid output with only required fields."""
        output = IngredientDetectionOutput(
            ingredients=["egg", "milk"],
            confidence_scores={"egg": 0.98, "milk": 0.95},
        )
        assert output.ingredients == ["egg", "milk"]
        assert output.image_description is None

    def test_valid_output_partial_confidence_scores(self):
        """Test that missing confidence scores raises error (all required)."""
        with pytest.raises(ValidationError):
            IngredientDetectionOutput(
                ingredients=["chicken", "rice", "soy sauce"],
                confidence_scores={
                    "chicken": 0.92,
                    "rice": 0.88,
                },
                image_description="Asian dish",
            )

    def test_valid_output_empty_ingredients(self):
        """Test that empty ingredients list raises error (min_length=1)."""
        with pytest.raises(ValidationError):
            IngredientDetectionOutput(
                ingredients=[],
                confidence_scores={},
            )

    def test_invalid_missing_ingredients(self):
        """Test that missing ingredients raises error."""
        with pytest.raises(ValidationError):
            IngredientDetectionOutput(
                confidence_scores={"tomato": 0.9},
            )

    def test_invalid_missing_confidence_scores(self):
        """Test that missing confidence_scores raises error."""
        with pytest.raises(ValidationError):
            IngredientDetectionOutput(
                ingredients=["tomato"],
            )

    def test_invalid_ingredients_not_list(self):
        """Test that ingredients as non-list raises error."""
        with pytest.raises(ValidationError):
            IngredientDetectionOutput(
                ingredients="tomato, garlic",
                confidence_scores={"tomato": 0.9},
            )

    def test_valid_confidence_scores_string_coercion(self):
        """Test that confidence_scores with string values is coerced to float by Pydantic."""
        output = IngredientDetectionOutput(
            ingredients=["tomato"],
            confidence_scores={"tomato": "0.9"},
        )
        assert output.confidence_scores["tomato"] == 0.9
        assert isinstance(output.confidence_scores["tomato"], float)

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization and deserialization roundtrip."""
        original = IngredientDetectionOutput(
            ingredients=["pepper", "onion"],
            confidence_scores={"pepper": 0.85, "onion": 0.78},
            image_description="Vegetable ingredients",
        )
        json_str = original.model_dump_json()
        deserialized = IngredientDetectionOutput.model_validate_json(json_str)
        assert deserialized.ingredients == original.ingredients
        assert deserialized.confidence_scores == original.confidence_scores


class TestJSONSchemaGeneration:
    """Test JSON schema generation for OpenAPI documentation."""

    def test_recipe_response_schema(self):
        """Test that RecipeResponse generates valid JSON schema."""
        schema = RecipeResponse.model_json_schema()
        assert schema is not None
        assert "properties" in schema
        assert "recipes" in schema["properties"]
        assert "execution_time_ms" in schema["properties"]
        assert "required" in schema
        assert "execution_time_ms" in schema["required"]

    def test_ingredient_detection_output_schema(self):
        """Test that IngredientDetectionOutput generates valid JSON schema."""
        schema = IngredientDetectionOutput.model_json_schema()
        assert schema is not None
        assert "properties" in schema
        assert "ingredients" in schema["properties"]
        assert "confidence_scores" in schema["properties"]
