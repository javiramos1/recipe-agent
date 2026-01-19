"""Data models and schemas for recipe recommendation service.

Defines Pydantic models for request/response validation and domain objects.
All models use Pydantic v2 for strict validation and OpenAPI schema generation.
"""

from typing import List, Optional
from pydantic import BaseModel


class RecipeRequest(BaseModel):
    """Request schema for recipe recommendations.
    
    Validates incoming requests with ingredient list and optional preferences.
    """
    ingredients: List[str]
    diet: Optional[str] = None
    cuisine: Optional[str] = None
    meal_type: Optional[str] = None
    intolerances: Optional[str] = None


class Ingredient(BaseModel):
    """Domain model for a detected ingredient.
    
    Represents an ingredient extracted from an image with confidence score.
    """
    name: str
    confidence: float


class Recipe(BaseModel):
    """Domain model for a recipe.
    
    Represents a complete recipe with ingredients, instructions, and metadata.
    """
    title: str
    description: Optional[str] = None
    ingredients: List[str]
    instructions: List[str]
    prep_time_min: int
    cook_time_min: int
    source_url: Optional[str] = None


class RecipeResponse(BaseModel):
    """Response schema for recipe recommendations.
    
    Contains recipes, detected ingredients, and session metadata.
    """
    recipes: List[Recipe]
    ingredients: List[str]
    preferences: dict[str, str]
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    execution_time_ms: int


class IngredientDetectionOutput(BaseModel):
    """Output schema for ingredient detection tool.
    
    Contains detected ingredients with confidence scores and description.
    """
    ingredients: List[str]
    confidence_scores: dict[str, float]
    image_description: Optional[str] = None
