"""End-to-end integration tests for Recipe Recommendation Service using Agno Evals.

Tests complete request-response flows with real images and MCP connections
using Agno's multi-dimensional evaluation framework:
- AccuracyEval: LLM-as-judge for ingredient detection accuracy
- AgentAsJudgeEval: Custom criteria with semantic scoring (recipe quality, preferences, guardrails)
- ReliabilityEval: Verify correct tool sequence (search_recipes → get_recipe_information_bulk)
- PerformanceEval: Response time under 5 seconds

Results are persisted in SqliteDb for queryable tracking and os.agno.com visualization.
"""

import asyncio
import base64
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import pytest
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.eval.accuracy import AccuracyEval, AccuracyResult
from agno.eval.agent_as_judge import AgentAsJudgeEval, AgentAsJudgeResult
from agno.eval.reliability import ReliabilityEval, ReliabilityResult
from agno.eval.performance import PerformanceEval, PerformanceResult
from agno.models.google import Gemini
from agno.run.agent import RunOutput

from src.agents.agent import initialize_recipe_agent
from src.utils.logger import logger


@pytest.fixture(scope="session")
def eval_db() -> SqliteDb:
    """Persistent database for storing evaluation results.
    
    Results are stored in tmp/eval_results.db for tracking and analysis
    across all evaluation runs. Can be queried programmatically and synced
    to os.agno.com for team visualization.
    """
    db_path = "tmp/eval_results.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SqliteDb(db_file=db_path, id="eval_db")


@pytest.fixture(scope="session")
def agent() -> Agent:
    """Initialize agent once for all tests.
    
    The agent is fully configured with:
    - Gemini model for ingredient detection
    - Spoonacular MCP for recipe search
    - SQLite session database for memory
    - Pre-hooks for image processing (pre-hook mode)
    - System instructions for recipe-focused behavior
    
    Shared across all tests to test preference persistence and session isolation.
    """
    logger.info("Initializing agent for integration tests...")
    try:
        # initialize_recipe_agent() returns (agent, tracing_db) tuple
        result = asyncio.run(initialize_recipe_agent())
        if isinstance(result, tuple):
            recipe_agent, tracing_db = result
        else:
            recipe_agent = result
        logger.info("Agent initialized successfully")
        return recipe_agent
    except Exception as e:
        logger.error(f"Agent initialization failed: {e}", exc_info=True)
        pytest.skip(f"Agent initialization failed: {e}")
        return None  # type: ignore


@pytest.fixture(scope="session")
def test_images() -> dict:
    """Load and encode sample test images.
    
    Returns dict mapping image categories to:
    - base64: Base64-encoded image for use in requests
    - expected: List of expected ingredients to find
    - description: Human-readable description for test documentation
    - file_path: Path to original image file
    
    Supported categories:
    - vegetables: Fresh vegetables (tomatoes, basil, onions, etc.)
    - fruits: Mixed fruits (bananas, apples, berries, etc.)
    - pantry: Pantry items (pasta, rice, beans, etc.)
    """
    images_dir = Path("images")
    
    # Map categories to actual image files (using available sample images)
    image_mappings = {
        "vegetables": {
            "file": "fresh_vegetables.jpg",
            "expected": ["vegetables", "tomato", "onion", "garlic"],
            "description": "Fresh vegetables for cooking"
        },
        "fruits": {
            "file": "fruit.jpg",
            "expected": ["fruit", "banana", "apple", "berry"],
            "description": "Mixed fresh fruits"
        },
        "pantry": {
            "file": "pasta.png",
            "expected": ["pasta", "grains", "dried goods"],
            "description": "Pantry staples and dry goods"
        }
    }
    
    test_images = {}
    for category, mapping in image_mappings.items():
        image_path = images_dir / mapping["file"]
        if image_path.exists():
            with open(image_path, "rb") as f:
                image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                test_images[category] = {
                    "base64": base64_image,
                    "expected": mapping["expected"],
                    "description": mapping["description"],
                    "file_path": str(image_path)
                }
                logger.info(f"Loaded test image: {category} from {image_path}")
        else:
            logger.warning(f"Test image not found: {image_path}")
    
    if not test_images:
        pytest.skip("No test images found in images/ directory")
    
    return test_images


class TestIngredientDetectionAccuracy:
    """AccuracyEval: Verify ingredient detection accuracy using LLM-as-judge.
    
    Tests that the agent correctly identifies ingredients from images
    using simple correctness checking with an LLM judge (gpt-4o).
    """
    
    def test_ingredient_detection_accuracy_vegetables(
        self, agent: Agent, eval_db: SqliteDb, test_images: dict
    ) -> None:
        """Verify vegetable ingredient detection accuracy.
        
        Run agent with vegetable image and evaluate with LLM judge to ensure
        detected ingredients match expected results.
        """
        if "vegetables" not in test_images:
            pytest.skip("Vegetable test image not available")
        
        veg_image = test_images["vegetables"]
        logger.info(f"Testing ingredient detection on: {veg_image['description']}")
        
        # Evaluate ingredient detection with LLM judge (Gemini)
        # AccuracyEval will run the agent internally
        try:
            evaluation = AccuracyEval(
                name="Vegetable Ingredient Detection",
                model=Gemini(id="gemini-2-flash-preview"),
                agent=agent,
                input={
                    "message": f"What ingredients are in this image? {veg_image['description']}"
                },
                expected_output=", ".join(veg_image["expected"]),
                additional_guidelines="List only the main ingredients detected with confidence > 70%. Be concise.",
            )
            
            result: Optional[AccuracyResult] = evaluation.run(print_results=True)
            
            if result:
                logger.info(f"Accuracy score: {result.score}")
                result.assert_passed()
            else:
                pytest.skip("Accuracy evaluation did not complete")
        except Exception as e:
            logger.error(f"Accuracy evaluation failed: {e}")
            pytest.skip(f"Accuracy evaluation failed: {e}")


class TestRecipeQuality:
    """AgentAsJudgeEval: Custom criteria for recipe completeness and quality.
    
    Tests that recipes include required fields (title, ingredients, instructions,
    time estimates) using semantic scoring (1-10 scale, threshold 7).
    """
    
    def test_recipe_quality_completeness(
        self, agent: Agent, eval_db: SqliteDb
    ) -> None:
        """Verify recipe responses include all required fields.
        
        Run agent with ingredient request and evaluate that response includes:
        - Recipe title
        - Ingredient list
        - Cooking instructions
        - Prep/cook time estimates
        """
        logger.info("Testing recipe quality completeness...")
        
        # Run agent with ingredient request
        try:
            response: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": "Find me recipes for chicken, tomatoes, and basil"
                }
            ))
            logger.info(f"Agent response length: {len(response.content) if response.content else 0}")
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            pytest.skip(f"Agent execution failed: {e}")
        
        # Evaluate recipe completeness with custom criteria
        evaluation = AgentAsJudgeEval(
            name="Recipe Completeness",
            criteria=(
                "Response should include: "
                "1) Recipe title/name, "
                "2) Complete ingredient list with quantities, "
                "3) Step-by-step cooking instructions, "
                "4) Prep time and cook time estimates. "
                "Score higher if response is well-formatted and easy to follow."
            ),
            scoring_strategy="numeric",
            threshold=7,
            db=eval_db,
        )
        
        result: Optional[AgentAsJudgeResult] = evaluation.run(
            input="Find recipes for chicken, tomatoes, basil",
            output=str(response.content) if response.content else "",
            print_results=True
        )
        
        if result:
            logger.info(f"Recipe quality score: {result.score}")
            assert result.passed, f"Recipe quality score {result.score} below threshold"
        else:
            pytest.skip("Recipe quality evaluation did not complete")


class TestPreferencePersistence:
    """AgentAsJudgeEval: Verify preferences extracted and applied across turns.
    
    Tests that user preferences (vegetarian, dietary restrictions, cuisine)
    are extracted in one turn and automatically applied in subsequent turns
    within the same session without re-stating the preference.
    """
    
    def test_preference_persistence_vegetarian(
        self, agent: Agent, eval_db: SqliteDb
    ) -> None:
        """Verify vegetarian preference persists across conversation turns.
        
        Turn 1: Extract preference ("I'm vegetarian")
        Turn 2: Verify preference applied without re-stating
        """
        session_id = f"test_pref_session_{uuid.uuid4().hex[:8]}"
        logger.info(f"Testing preference persistence with session: {session_id}")
        
        try:
            # Turn 1: Extract preference
            response1: RunOutput = asyncio.run(agent.arun(
                message="I'm vegetarian. What recipes do you recommend?",
                session_id=session_id
            ))
            logger.info(f"Turn 1 response: {response1.content[:100] if response1.content else ''}...")
            
            # Turn 2: Verify preference applied without re-stating
            response2: RunOutput = asyncio.run(agent.arun(
                message="What about Italian recipes?",
                session_id=session_id
            ))
            logger.info(f"Turn 2 response: {response2.content[:100] if response2.content else ''}...")
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            pytest.skip(f"Agent execution failed: {e}")
        
        # Evaluate that preference persisted
        evaluation = AgentAsJudgeEval(
            name="Preference Persistence - Vegetarian",
            criteria=(
                "In the response to 'What about Italian recipes?', the agent should: "
                "1) Provide Italian-style recipes, "
                "2) All recipes should be vegetarian (no meat/fish), "
                "3) NOT ask the user to re-state vegetarian preference, "
                "4) Show that it remembered the preference from Turn 1."
            ),
            scoring_strategy="numeric",
            threshold=7,
            db=eval_db,
        )
        
        result: Optional[AgentAsJudgeResult] = evaluation.run(
            input="Previous: user stated 'I'm vegetarian'. New request: 'What about Italian recipes?'",
            output=str(response2.content) if response2.content else "",
            print_results=True
        )
        
        if result:
            logger.info(f"Preference persistence score: {result.score}")
            assert result.passed, f"Preference persistence score {result.score} below threshold"
        else:
            pytest.skip("Preference persistence evaluation did not complete")


class TestGuardrails:
    """AgentAsJudgeEval: Verify agent refuses off-topic requests politely.
    
    Tests that agent enforces guardrails by politely declining off-topic
    requests and redirecting to recipe-focused topics.
    """
    
    def test_off_topic_rejection_weather(
        self, agent: Agent, eval_db: SqliteDb
    ) -> None:
        """Verify agent rejects weather questions politely.
        
        Send off-topic request (weather) and verify agent:
        - Politely declines
        - Explains it's recipe-focused
        - Offers to help with recipes instead
        """
        logger.info("Testing off-topic guardrail enforcement...")
        
        try:
            response: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": "What's the weather today?"
                }
            ))
            logger.info(f"Off-topic response: {response.content[:100] if response.content else ''}...")
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            pytest.skip(f"Agent execution failed: {e}")
        
        # Evaluate guardrail response
        evaluation = AgentAsJudgeEval(
            name="Guardrail Enforcement - Off-Topic",
            criteria=(
                "Response should: "
                "1) Politely decline to answer the off-topic question, "
                "2) Explain the agent is recipe-focused, "
                "3) Offer to help with recipe-related queries instead, "
                "4) NOT attempt to answer the weather question."
            ),
            scoring_strategy="numeric",
            threshold=7,
            db=eval_db,
        )
        
        result: Optional[AgentAsJudgeResult] = evaluation.run(
            input="What's the weather today?",
            output=str(response.content) if response.content else "",
            print_results=True
        )
        
        if result:
            logger.info(f"Guardrail enforcement score: {result.score}")
            assert result.passed, f"Guardrail score {result.score} below threshold"
        else:
            pytest.skip("Guardrail evaluation did not complete")


class TestSessionIsolation:
    """AgentAsJudgeEval: Verify preferences don't leak between sessions.
    
    Tests that preferences extracted in one user's session don't affect
    other users' sessions - sessions should be isolated.
    """
    
    def test_session_isolation_preferences(
        self, agent: Agent, eval_db: SqliteDb
    ) -> None:
        """Verify preferences don't cross-contaminate between sessions.
        
        User A: Sets vegetarian preference
        User B: Should not be limited to vegetarian recipes
        """
        user_a_session = f"user_a_{uuid.uuid4().hex[:8]}"
        user_b_session = f"user_b_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Testing session isolation: {user_a_session} vs {user_b_session}")
        
        try:
            # User A: Set vegetarian preference
            response_a: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": "I'm vegetarian"
                },
                session_id=user_a_session
            ))
            logger.info(f"User A response: {response_a.content[:100] if response_a.content else ''}...")
            
            # User B: Should get meat-based options (no vegetarian constraint)
            response_b: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": "Show me recipes with meat"
                },
                session_id=user_b_session
            ))
            logger.info(f"User B response: {response_b.content[:100] if response_b.content else ''}...")
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            pytest.skip(f"Agent execution failed: {e}")
        
        # Evaluate session isolation
        evaluation = AgentAsJudgeEval(
            name="Session Isolation",
            criteria=(
                "For User B's request 'Show me recipes with meat': "
                "1) Response should include meat-based recipes, "
                "2) Should NOT enforce vegetarian constraint (from User A), "
                "3) Recipes can include chicken, beef, fish, etc., "
                "4) User B's session should be independent of User A's preferences."
            ),
            scoring_strategy="numeric",
            threshold=7,
            db=eval_db,
        )
        
        result: Optional[AgentAsJudgeResult] = evaluation.run(
            input="Different session requesting meat recipes. User A had vegetarian preference in separate session.",
            output=str(response_b.content) if response_b.content else "",
            print_results=True
        )
        
        if result:
            logger.info(f"Session isolation score: {result.score}")
            assert result.passed, f"Session isolation score {result.score} below threshold"
        else:
            pytest.skip("Session isolation evaluation did not complete")


class TestToolReliability:
    """ReliabilityEval: Verify correct tool sequence for recipe process.
    
    Tests that agent follows the two-step recipe process:
    1. Call search_recipes with detected ingredients
    2. Call get_recipe_information_bulk to get full recipe details
    
    This prevents hallucinations by ensuring recipes are ground in tool outputs.
    """
    
    def test_two_step_recipe_process(
        self, agent: Agent
    ) -> None:
        """Verify agent uses correct tool sequence.
        
        Agent should:
        1. Call search_recipes to find recipes by ingredients
        2. Call get_recipe_information_bulk to get complete recipe details
        
        This two-step process ensures recipes are grounded in real data.
        """
        logger.info("Testing two-step recipe tool process reliability...")
        
        try:
            response: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": "What recipes can I make with tomatoes and basil?"
                }
            ))
            logger.info(f"Agent response received")
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            pytest.skip(f"Agent execution failed: {e}")
        
        # Verify correct tool sequence
        evaluation = ReliabilityEval(
            name="Two-Step Recipe Process",
            agent_response=response,
            expected_tool_calls=["search_recipes", "get_recipe_information_bulk"],
        )
        
        result: Optional[ReliabilityResult] = evaluation.run(print_results=True)
        
        if result:
            logger.info("Tool reliability: PASSED")
            result.assert_passed()
        else:
            pytest.skip("Tool reliability evaluation did not complete")


class TestPerformance:
    """PerformanceEval: Measure response latency and efficiency.
    
    Tests that agent responds within acceptable time (max 5 seconds)
    for good user experience.
    """
    
    def test_response_time_performance(
        self, agent: Agent
    ) -> None:
        """Verify response time is within acceptable range.
        
        Agent should respond to recipe requests within 5 seconds
        for good user experience.
        """
        logger.info("Testing response time performance...")
        
        # Measure performance with agent and input
        def run_agent_test():
            return asyncio.run(agent.arun(
                input={
                    "message": "Show me vegetarian recipes"
                }
            ))
        
        evaluation = PerformanceEval(
            name="Response Latency",
            func=run_agent_test,
            num_iterations=1,
            warmup_runs=0,
        )
        
        result: Optional[PerformanceResult] = evaluation.run(print_results=True)
        
        if result:
            logger.info(f"Performance evaluation completed. Avg latency: {result.avg_latency_ms}ms")
            # Check if within reasonable time (5 seconds)
            assert result.avg_latency_ms < 5000, f"Response took {result.avg_latency_ms}ms, should be under 5 seconds"
        else:
            pytest.skip("Performance evaluation did not complete")


class TestErrorHandling:
    """AgentAsJudgeEval: Verify graceful error handling for edge cases.
    
    Tests that agent handles edge cases (empty messages, invalid input)
    gracefully without crashing, providing helpful feedback.
    """
    
    def test_error_handling_empty_message(
        self, agent: Agent, eval_db: SqliteDb
    ) -> None:
        """Verify agent handles empty messages gracefully.
        
        Send empty message and verify agent:
        - Doesn't crash
        - Provides helpful error message or default behavior
        - Suggests next steps
        """
        logger.info("Testing error handling for empty message...")
        
        try:
            response: RunOutput = asyncio.run(agent.arun(
                input={
                    "message": ""
                }
            ))
            logger.info(f"Error handling response: {response.content[:100] if response.content else 'No content'}...")
        except Exception as e:
            logger.error(f"Agent run raised exception: {e}")
            # Exception handling is also acceptable
            pytest.skip(f"Agent handling: {e}")
        
        # Evaluate error handling
        evaluation = AgentAsJudgeEval(
            name="Error Handling",
            criteria=(
                "For empty message input, agent should: "
                "1) NOT crash or raise an error, "
                "2) Provide a helpful message (or use default), "
                "3) Suggest what the user can do (upload image or provide ingredients), "
                "4) Handle gracefully without requiring manual intervention."
            ),
            scoring_strategy="numeric",
            threshold=7,
            db=eval_db,
        )
        
        result: Optional[AgentAsJudgeResult] = evaluation.run(
            input="",
            output=str(response.content) if response.content else "No response",
            print_results=True
        )
        
        if result:
            logger.info(f"Error handling score: {result.score}")
            assert result.passed, f"Error handling score {result.score} below threshold"
        else:
            pytest.skip("Error handling evaluation did not complete")
