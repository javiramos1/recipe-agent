"""Unit tests for Pydantic models validation."""

import json
import pytest
from pydantic import ValidationError

from src.models.models import (
    RecipeRequest,
    Ingredient,
    Recipe,
    RecipeResponse,
    IngredientDetectionOutput,
)


class TestRecipeRequest:
    """Test RecipeRequest model validation."""

    def test_valid_request_required_fields_only(self):
        """Test valid request with only required ingredients field."""
        request = RecipeRequest(ingredients=["tomato", "basil"])
        assert request.ingredients == ["tomato", "basil"]
        assert request.diet is None
        assert request.cuisine is None
        assert request.meal_type is None
        assert request.intolerances is None

    def test_valid_request_with_all_fields(self):
        """Test valid request with all optional fields populated."""
        request = RecipeRequest(
            ingredients=["chicken", "rice"],
            diet="keto",
            cuisine="asian",
            meal_type="main course",
            intolerances="gluten, peanuts",
        )
        assert request.ingredients == ["chicken", "rice"]
        assert request.diet == "keto"
        assert request.cuisine == "asian"
        assert request.meal_type == "main course"
        assert request.intolerances == "gluten, peanuts"

    def test_valid_request_with_partial_optional_fields(self):
        """Test valid request with some optional fields."""
        request = RecipeRequest(
            ingredients=["salmon"],
            diet="mediterranean",
            cuisine="italian",
        )
        assert request.ingredients == ["salmon"]
        assert request.diet == "mediterranean"
        assert request.cuisine == "italian"
        assert request.meal_type is None
        assert request.intolerances is None

    def test_invalid_missing_required_ingredients(self):
        """Test that missing required ingredients field raises error."""
        with pytest.raises(ValidationError):
            RecipeRequest(diet="vegan")

    def test_invalid_ingredients_not_list(self):
        """Test that ingredients not as list raises error."""
        with pytest.raises(ValidationError):
            RecipeRequest(ingredients="tomato, basil")

    def test_valid_empty_ingredients_list(self):
        """Test that empty ingredients list is valid (Pydantic allows it)."""
        request = RecipeRequest(ingredients=[])
        assert request.ingredients == []

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization and deserialization roundtrip."""
        original = RecipeRequest(
            ingredients=["egg", "cheese"],
            diet="vegetarian",
        )
        json_str = original.model_dump_json()
        deserialized = RecipeRequest.model_validate_json(json_str)
        assert deserialized.ingredients == original.ingredients
        assert deserialized.diet == original.diet


class TestIngredient:
    """Test Ingredient model validation."""

    def test_valid_ingredient(self):
        """Test valid ingredient with name and confidence."""
        ingredient = Ingredient(name="tomato", confidence=0.95)
        assert ingredient.name == "tomato"
        assert ingredient.confidence == 0.95

    def test_valid_ingredient_min_confidence(self):
        """Test valid ingredient with minimum confidence."""
        ingredient = Ingredient(name="basil", confidence=0.0)
        assert ingredient.confidence == 0.0

    def test_valid_ingredient_max_confidence(self):
        """Test valid ingredient with maximum confidence."""
        ingredient = Ingredient(name="garlic", confidence=1.0)
        assert ingredient.confidence == 1.0

    def test_invalid_missing_name(self):
        """Test that missing name raises error."""
        with pytest.raises(ValidationError):
            Ingredient(confidence=0.8)

    def test_invalid_missing_confidence(self):
        """Test that missing confidence raises error."""
        with pytest.raises(ValidationError):
            Ingredient(name="onion")

    def test_valid_confidence_string_coercion(self):
        """Test that confidence as string is coerced to float by Pydantic."""
        ingredient = Ingredient(name="pepper", confidence="0.8")
        assert ingredient.confidence == 0.8
        assert isinstance(ingredient.confidence, float)


class TestRecipe:
    """Test Recipe model validation."""

    def test_valid_recipe_all_fields(self):
        """Test valid recipe with all fields populated."""
        recipe = Recipe(
            title="Tomato Pasta",
            description="Classic Italian pasta with fresh tomatoes",
            ingredients=["pasta", "tomato", "garlic", "olive oil"],
            instructions=["Boil water", "Cook pasta", "Make sauce", "Combine"],
            prep_time_min=10,
            cook_time_min=20,
            source_url="https://example.com/recipe",
        )
        assert recipe.title == "Tomato Pasta"
        assert recipe.description == "Classic Italian pasta with fresh tomatoes"
        assert len(recipe.ingredients) == 4
        assert len(recipe.instructions) == 4
        assert recipe.prep_time_min == 10
        assert recipe.cook_time_min == 20
        assert recipe.source_url == "https://example.com/recipe"

    def test_valid_recipe_required_fields_only(self):
        """Test valid recipe with only required fields."""
        recipe = Recipe(
            title="Simple Salad",
            ingredients=["lettuce", "tomato"],
            instructions=["Chop vegetables", "Mix together"],
            prep_time_min=5,
            cook_time_min=0,
        )
        assert recipe.title == "Simple Salad"
        assert recipe.description is None
        assert recipe.source_url is None

    def test_valid_recipe_optional_fields_as_none(self):
        """Test recipe with explicitly set None for optional fields."""
        recipe = Recipe(
            title="Breakfast",
            ingredients=["eggs"],
            instructions=["Cook"],
            prep_time_min=0,
            cook_time_min=5,
            description=None,
            source_url=None,
        )
        assert recipe.description is None
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
        """Test that prep_time_min as string is coerced to int by Pydantic."""
        recipe = Recipe(
            title="Test",
            ingredients=["test"],
            instructions=["test"],
            prep_time_min="10",
            cook_time_min=5,
        )
        assert recipe.prep_time_min == 10
        assert isinstance(recipe.prep_time_min, int)

    def test_valid_cook_time_string_coercion(self):
        """Test that cook_time_min as string is coerced to int by Pydantic."""
        recipe = Recipe(
            title="Test",
            ingredients=["test"],
            instructions=["test"],
            prep_time_min=5,
            cook_time_min="10",
        )
        assert recipe.cook_time_min == 10
        assert isinstance(recipe.cook_time_min, int)


class TestRecipeResponse:
    """Test RecipeResponse model validation."""

    def test_valid_response_with_recipes(self):
        """Test valid response with recipes and metadata."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=["ingredient1"],
            instructions=["instruction1"],
            prep_time_min=5,
            cook_time_min=10,
        )
        response = RecipeResponse(
            response="Here are some recipes for you.",
            recipes=[recipe],
            ingredients=["ingredient1", "ingredient2"],
            preferences={"diet": "vegetarian", "cuisine": "italian"},
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
            title="Test",
            ingredients=["test"],
            instructions=["test"],
            prep_time_min=0,
            cook_time_min=0,
        )
        response = RecipeResponse(
            response="Here's a test recipe.",
            recipes=[recipe],
            ingredients=["test"],
            preferences={},
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
            preferences={},
            execution_time_ms=50,
        )
        assert response.recipes == []
        assert response.ingredients == []
        assert response.response == "No recipes found for your request."

    def test_valid_response_multiple_recipes(self):
        """Test valid response with multiple recipes."""
        recipes = [
            Recipe(
                title=f"Recipe {i}",
                ingredients=[f"ingredient{i}"],
                instructions=[f"instruction{i}"],
                prep_time_min=i,
                cook_time_min=i * 2,
            )
            for i in range(3)
        ]
        response = RecipeResponse(
            response="Found 3 great recipes for you!",
            recipes=recipes,
            ingredients=["ing1", "ing2", "ing3"],
            preferences={"diet": "keto"},
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
            preferences={},
            execution_time_ms="1500",
        )
        assert response.execution_time_ms == 1500
        assert isinstance(response.execution_time_ms, int)

    def test_json_serialization_roundtrip(self):
        """Test JSON serialization and deserialization roundtrip."""
        recipe = Recipe(
            title="Roundtrip Test",
            ingredients=["test"],
            instructions=["test"],
            prep_time_min=5,
            cook_time_min=10,
        )
        original = RecipeResponse(
            response="Roundtrip test response.",
            recipes=[recipe],
            ingredients=["test"],
            preferences={"diet": "vegan"},
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
        """Test valid output where not all ingredients have confidence scores."""
        output = IngredientDetectionOutput(
            ingredients=["chicken", "rice", "soy sauce"],
            confidence_scores={
                "chicken": 0.92,
                "rice": 0.88,
            },
            image_description="Asian dish",
        )
        assert len(output.ingredients) == 3
        assert len(output.confidence_scores) == 2

    def test_valid_output_empty_ingredients(self):
        """Test valid output with empty ingredients list."""
        output = IngredientDetectionOutput(
            ingredients=[],
            confidence_scores={},
        )
        assert output.ingredients == []
        assert output.confidence_scores == {}

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

    def test_recipe_request_schema(self):
        """Test that RecipeRequest generates valid JSON schema."""
        schema = RecipeRequest.model_json_schema()
        assert schema is not None
        assert "properties" in schema
        assert "ingredients" in schema["properties"]
        assert "required" in schema
        assert "ingredients" in schema["required"]

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
