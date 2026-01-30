"""Data models and schemas for recipe recommendation service.

Defines Pydantic models for request/response validation and domain objects.
All models use Pydantic v2 for strict validation and OpenAPI schema generation.
"""

from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ChatMessage(BaseModel):
    """Minimal input schema for conversational recipe recommendation.

    Accepts natural language message and optional comma-separated image URLs/base64 strings.
    Message is optional if images are provided (defaults to "What can I cook with these ingredients?").
    Preferences and ingredients are extracted from the message or retrieved from agent memory.

    This minimal schema allows full conversational flexibility without pre-structuring input.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    message: Annotated[
        Optional[str],
        Field(
            None,
            min_length=1,
            max_length=2000,
            description="Natural language message from user (1-2000 chars, optional if images provided)",
        ),
    ]
    images: Annotated[
        Optional[str | list[str]],
        Field(None, description="Optional comma-separated image URLs/base64 or list of URLs (max 10 images)"),
    ]

    @model_validator(mode="before")
    @classmethod
    def set_default_message_before(cls, data: dict) -> dict:
        """Set default message if not provided but images are present."""
        if isinstance(data, dict):
            message = data.get("message")
            images = data.get("images")

            # If message is missing or empty, but images are present, set default message
            if not message or (isinstance(message, str) and not message.strip()):
                if images:
                    if isinstance(images, list) and len(images) > 0:
                        data["message"] = "What can I cook with these ingredients?"
                    elif isinstance(images, str) and images.strip():
                        data["message"] = "What can I cook with these ingredients?"

        return data

    @model_validator(mode="after")
    def validate_message_or_images(self) -> "ChatMessage":
        """Ensure either message or images are provided."""
        if not self.message and not self.images:
            raise ValueError("Either message or images field must be provided")
        return self

    @staticmethod
    def _is_valid_image(image_str: str) -> bool:
        """Check if image string is either a valid URL or base64-encoded data."""
        if not image_str or not isinstance(image_str, str):
            return False

        # Check if it's a URL (http:// or https://)
        if image_str.startswith(("http://", "https://")):
            return True

        # Check if it's base64-encoded (data URI or plain base64)
        if image_str.startswith("data:"):
            # data: URL format
            return True

        # Check if it's plain base64 (alphanumeric, +, /, and = for padding)
        if all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in image_str):
            # Additional check: base64 should have proper length (multiple of 4 after stripping padding)
            clean = image_str.rstrip("=")
            if len(clean) % 4 == 0 or (len(image_str) % 4 == 0):
                return True

        return False

    @field_validator("images", mode="before")
    @classmethod
    def parse_images(cls, images: Optional[str | list[str]]) -> Optional[list[str]]:
        """Parse comma-separated images string or list into normalized list.

        Validates that each image is either a URL (http/https) or base64-encoded data.
        """
        if not images:
            return []

        # If already a list, return as-is
        if isinstance(images, list):
            image_list = [img.strip() if isinstance(img, str) else str(img) for img in images if img]
            if len(image_list) > 10:
                raise ValueError("Maximum 10 images allowed")
            # Validate each image
            for img in image_list:
                if not cls._is_valid_image(img):
                    raise ValueError(
                        f"Invalid image: must be a URL (http/https) or base64-encoded data. Got: {img[:50]}..."
                    )
            return image_list

        # If string, split by comma
        if isinstance(images, str):
            if not images.strip():
                return []
            image_list = [img.strip() for img in images.split(",") if img.strip()]
            if len(image_list) > 10:
                raise ValueError("Maximum 10 images allowed")
            # Validate each image
            for img in image_list:
                if not cls._is_valid_image(img):
                    raise ValueError(
                        f"Invalid image: must be a URL (http/https) or base64-encoded data. Got: {img[:50]}..."
                    )
            return image_list

        return []


class Recipe(BaseModel):
    """Domain model for a recipe.

    Supports both basic search results (Step 1) and full recipe details (Step 2).
    - Step 1: Only id and title are required (from search_recipes)
      - Optional basic fields: ready_in_minutes, servings, image
    - Step 2: All fields populated including ingredients/instructions (from get_recipe_information)

    All fields except id and title are optional. A Recipe object with just id and title is VALID.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: Annotated[int, Field(description="Recipe ID from Spoonacular API")]
    title: Annotated[str, Field(min_length=1, max_length=200, description="Recipe name or title (1-200 chars)")]
    ready_in_minutes: Annotated[
        Optional[int],
        Field(
            None,
            ge=0,
            le=1440,
            description="Total time (prep + cook) in minutes (0-1440, only set when get_recipe_information is called)",
        ),
    ]
    servings: Annotated[
        Optional[int],
        Field(
            None, ge=1, le=100, description="Number of servings (1-100, only set when get_recipe_information is called)"
        ),
    ]
    image: Annotated[
        Optional[str],
        Field(None, max_length=500, description="URL to recipe image (only set when get_recipe_information is called)"),
    ]
    summary: Annotated[
        Optional[str],
        Field(
            None,
            max_length=1000,
            description="Brief description or summary (max 1000 chars, only set when get_recipe_information is called)",
        ),
    ]
    ingredients: Annotated[
        Optional[List[str]],
        Field(
            None,
            max_length=100,
            description="List of ingredients with quantities (max 100 items, only set when get_recipe_information is called)",
        ),
    ]
    instructions: Annotated[
        Optional[List[str]],
        Field(
            None,
            max_length=100,
            description="Step-by-step cooking instructions (max 100 steps, only set when get_recipe_information is called)",
        ),
    ]
    source_url: Annotated[
        Optional[str],
        Field(
            None,
            max_length=500,
            description="URL to original recipe source (only set when get_recipe_information is called)",
        ),
    ]


class RecipeResponse(BaseModel):
    """Response schema for recipe recommendations.

    Contains structured recipes, detected ingredients, session metadata, and the LLM-generated response.
    The 'response' field is generated by the LLM and contains conversational text including:
    - Greeting/context
    - Formatted recipe details (if recipes found)
    - Any guardrails, follow-up questions, or suggestions

    The 'reasoning' field provides transparency about agent decisions.
    Enforces constraints on all fields for API consistency.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    response: Annotated[
        str,
        Field(
            description="Markdown-formatted final response presented to the user containing conversational text, recipe details, and suggestions (1-5000 chars)"
        ),
    ]
    recipes: Annotated[List[Recipe], Field(default_factory=list, description="List of recipe objects (max 50 recipes)")]
    ingredients: Annotated[
        List[str], Field(default_factory=list, description="List of detected or provided ingredients (max 100)")
    ]
    preferences: Annotated[
        Optional[List[str]],
        Field(default_factory=list, description="User preferences (diet, cuisine, meal_type, etc.)"),
    ]
    reasoning: Annotated[
        Optional[str], Field(None, description="Explanation of agent's decision-making (max 2000 chars)")
    ]
    session_id: Annotated[Optional[str], Field(None, description="Session identifier for conversation continuity")]
    run_id: Annotated[Optional[str], Field(None, description="Unique ID for this agent execution")]
    execution_time_ms: Annotated[
        int, Field(ge=0, le=300000, description="Execution time in milliseconds (0-300000, i.e., 0-5 min)")
    ]


class IngredientDetectionOutput(BaseModel):
    """Output schema for ingredient detection tool.

    Contains detected ingredients with confidence scores and description.
    Enforces strict validation on confidence scores and ingredient format.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    ingredients: Annotated[
        List[str], Field(min_length=1, max_length=50, description="List of detected ingredients (1-50 items)")
    ]
    confidence_scores: Annotated[
        dict[str, float], Field(description="Confidence scores for each ingredient (0.0 < score <= 1.0)")
    ]
    image_description: Annotated[
        Optional[str],
        Field(None, max_length=500, description="Natural language description of the image (max 500 chars)"),
    ]

    @field_validator("confidence_scores", mode="before")
    @classmethod
    def validate_confidence_scores(cls, v: dict) -> dict:
        """Validate confidence scores: each value must be 0.0 < score <= 1.0."""
        if not isinstance(v, dict):
            raise ValueError("confidence_scores must be a dictionary")

        validated = {}
        for ingredient, score in v.items():
            if not isinstance(ingredient, str):
                raise ValueError("Confidence score keys must be strings")

            try:
                f = float(score)
            except (ValueError, TypeError):
                raise ValueError(f"Confidence score must be numeric for {ingredient}")

            if not (0.0 < f <= 1.0):
                raise ValueError(f"Confidence score must be 0.0 < score <= 1.0, got {f} for {ingredient}")

            validated[ingredient.strip().lower()] = f

        return validated

    @model_validator(mode="after")
    def validate_scores_match_ingredients(self) -> "IngredientDetectionOutput":
        """Validate that all ingredients have confidence scores."""
        ingredient_set = set(ing.lower() for ing in self.ingredients)
        score_keys = set(key.lower() for key in self.confidence_scores.keys())

        # Allow scores to have extra entries, but all ingredients must have scores
        missing_scores = ingredient_set - score_keys
        if missing_scores:
            raise ValueError(f"Missing confidence scores for: {missing_scores}")

        return self
