# Implementation Plan - Image-Based Recipe Recommendation Service

**Target Audience:** LLM-based coding agent

**Goal:** Create independent, self-contained tasks that work around context window limitations, prevent hallucination through explicit specifications, and enable high-quality code implementation by breaking the system into focused, reviewable units.

This document provides independent, self-contained tasks for implementing a production-quality GenAI recipe recommendation service using AgentOS and Agno Agent. Each task includes:
- Clear requirements and context
- Input/output specifications
- Success criteria
- Dependencies on other tasks
- Key constraints and guardrails

---

## Overview of Solution

The solution is a single Python application (`python app.py`) that provides:
- **REST API** for programmatic access to recipe recommendations
- **Web UI (AGUI)** for interactive testing at `http://localhost:7777`
- **Stateful Agent** managing conversation memory and preference tracking
- **Image Processing** extracting ingredients via Gemini vision API
- **Recipe Search** via external Spoonacular MCP service

**Key Architecture:**
- Entry point: `app.py` (~150-200 lines, AgentOS application)
- Configuration: `config.py` (environment variables + .env file)
- Data models: `models.py` (Pydantic schemas)
- Ingredient detection: Pre-hook function in `ingredients.py`
- Tests: `tests/unit/` (Python unit tests) + `tests/integration/` (Agno evals)

**Technology Stack:**
- **Framework:** AgentOS (complete runtime providing REST API, Web UI, orchestration)
- **Agent:** Agno Agent (stateful orchestrator with built-in memory, retries, guardrails)
- **Vision API:** Google Gemini 1.5 Flash
- **Recipe Search:** Spoonacular MCP (external Node.js service via npx)
- **Database:** SQLite + LanceDB (dev), PostgreSQL + pgvector (production)
- **Testing:** pytest (unit), Agno evals (integration)

**Startup Validation:**
- External MCPs (Spoonacular) are startup-critical (fail if unreachable)
- Local tools (@tool functions) do not require startup validation
- AgentOS automatically validates MCP connections on `.serve()`

---

## Independent Task List

All tasks are independent and self-contained. Most tasks have optional dependencies listed, but each task provides complete context to execute standalone. The recommended execution order is listed, but tasks can be executed in parallel except where explicitly noted.

### Task 1: Project Structure & Dependencies Setup

**Objective:** Initialize project folders and create dependency manifests.

**Context:**
- Repository root: `/home/javi_rnr/poc/challenge/`
- No existing Python files in workspace
- Makefile and .github/copilot-instructions.md already exist

**Requirements:**
1. Create folder structure:
   - `app.py` (root level, for AgentOS application)
   - `config.py` (root level, for configuration)
   - `models.py` (root level, for Pydantic schemas)
   - `ingredients.py` (root level, for ingredient detection pre-hook)
   - `tests/unit/` (directory for unit tests)
   - `tests/integration/` (directory for integration tests)
   - `images/` (directory for test images)

2. Create `requirements.txt` with these dependencies:
   - agno (latest, with AgentOS and Agno Agent)
   - google-generativeai (for Gemini vision API)
   - python-dotenv (for .env file loading)
   - pydantic (for data validation)
   - pytest (for unit tests)
   - pytest-asyncio (for async test support)

3. Create `.env.example` with template values:
   - GEMINI_API_KEY (required, no default)
   - SPOONACULAR_API_KEY (required, no default)
   - GEMINI_MODEL=gemini-1.5-flash
   - PORT=7777
   - MAX_HISTORY=3
   - MAX_IMAGE_SIZE_MB=5
   - MIN_INGREDIENT_CONFIDENCE=0.7
   - DATABASE_URL (optional, for PostgreSQL in production)

4. Update `.gitignore` to exclude:
   - `.env` (user credentials)
   - `*.db` (SQLite databases)
   - `*.lance` (LanceDB vector databases)
   - `__pycache__/`
   - `*.pyc`

**Input:** None (repository initialization)

**Output:**
- Created folder structure
- Created requirements.txt with all dependencies
- Created .env.example with configuration template
- Updated .gitignore

**Success Criteria:**
- All folders exist and are empty except as needed
- requirements.txt has all listed dependencies
- .env.example has all required and optional variables
- .gitignore properly excludes sensitive and cache files

**Dependencies:**
- None (first task, foundational)

**Key Constraints:**
- No actual secrets in .env.example (use placeholder text like "your_key_here")
- Do not create .env file (user will copy from .env.example)
- Makefile is already present, do not modify it

---

### Task 2: Configuration Management Implementation (config.py)

**Objective:** Implement environment variable loading and configuration management.

**Context:**
- Python-dotenv handles .env file loading
- Environment variables override .env values (system env vars have priority)
- Required API keys: GEMINI_API_KEY, SPOONACULAR_API_KEY
- Optional: DATABASE_URL for production PostgreSQL

**Requirements:**
1. Load `.env` file using `python-dotenv.load_dotenv()`

2. Define `Config` class with these attributes (all using `os.getenv()`):
   - `GEMINI_API_KEY` (required string, no default)
   - `SPOONACULAR_API_KEY` (required string, no default)
   - `GEMINI_MODEL` (optional string, default: "gemini-1.5-flash")
   - `PORT` (optional int, default: 7777)
   - `MAX_HISTORY` (optional int, default: 3)
   - `MAX_IMAGE_SIZE_MB` (optional int, default: 5)
   - `MIN_INGREDIENT_CONFIDENCE` (optional float, default: 0.7)
   - `DATABASE_URL` (optional string, no default)

3. Implement `Config.validate()` method:
   - Raise `ValueError` if GEMINI_API_KEY is missing
   - Raise `ValueError` if SPOONACULAR_API_KEY is missing
   - Return without error if both keys present

4. Create module-level `config` instance:
   - `config = Config()`
   - Call `config.validate()` immediately
   - This instance is imported by other modules

5. Behavior specification:
   - System environment variables override .env file values
   - .env file is loaded from current directory
   - If .env file doesn't exist, load_dotenv() silently continues (no error)
   - All numeric values converted to correct types (int, float)
   - Default values used only if environment variable not set

**Input:**
- .env file (if exists, from Task 1)
- System environment variables (from developer setup)

**Output:**
- `config.py` file with Config class and module-level instance
- Ready to be imported: `from config import config`

**Success Criteria:**
- `python -c "from config import config; print(config.GEMINI_API_KEY)"` raises ValueError if key not set
- `python -c "from config import config; print(config.PORT)"` returns 7777 (default)
- Environment variables override .env values
- All numeric conversions work correctly

**Dependencies:**
- Task 1 (requires .env.example, requirements.txt)

**Key Constraints:**
- Do not validate API keys by making actual API calls (only check presence)
- Handle missing .env file gracefully (python-dotenv does this by default)
- Convert numeric values to correct types (int for PORT/MAX_HISTORY/MAX_IMAGE_SIZE_MB, float for MIN_INGREDIENT_CONFIDENCE)
- Export module-level `config` instance for import by other modules

---

### Task 2.5: Logging Infrastructure Implementation (logger.py)

**Objective:** Implement centralized logging with configurable format (text/JSON) and level.

**Context:**
- All application modules import and use the logger
- Logging is first-class infrastructure (not optional)
- Two output formats: Rich text (default) with colors and JSON for aggregation
- Configurable via environment variables
- Never logs sensitive data (API keys, passwords, images)

**Requirements:**

1. Update `requirements.txt` to include `rich` library for colored output

2. Update `.env.example` with logging configuration:
   - `LOG_LEVEL=INFO` (options: DEBUG, INFO, WARNING, ERROR)
   - `LOG_TYPE=text` (options: text, json)

3. Implement `logger.py` module with:

   a. `JSONFormatter` class:
      - Extends `logging.Formatter`
      - Outputs structured JSON with fields: timestamp (ISO format), level, logger name, message
      - Includes exception traceback if present
      - Optionally includes request_id and session_id if in record

   b. `RichTextFormatter` class:
      - Extends `logging.Formatter`
      - Outputs colored text with emoji icons (🔍 DEBUG, ℹ️ INFO, ⚠️ WARNING, ❌ ERROR)
      - Uses ANSI color codes (cyan, green, yellow, red)
      - Includes timestamp in format YYYY-MM-DD HH:MM:SS
      - Includes exception traceback if present

   c. `get_logger(name: str)` function:
      - Creates and configures logger instance
      - Reads LOG_LEVEL and LOG_TYPE from environment
      - Returns existing logger if already configured (singleton pattern)
      - Sets appropriate formatter based on LOG_TYPE
      - Returns logger instance for import by other modules

   d. Module-level `logger` instance:
      - `logger = get_logger("recipe_service")`
      - This instance is the main import for application code

**Input:**
- requirements.txt (update to include rich)
- .env.example (add LOG_LEVEL and LOG_TYPE)

**Output:**
- `logger.py` file with logging infrastructure
- Updated requirements.txt with rich library
- Updated .env.example with logging variables

**Success Criteria:**
- `python -c "from logger import logger; logger.info('test')"` outputs colored text (default)
- `LOG_TYPE=json python -c "from logger import logger; logger.info('test')"` outputs JSON
- `LOG_LEVEL=DEBUG LOG_TYPE=text python -c "from logger import logger; logger.debug('test')"` shows debug message
- `LOG_LEVEL=WARNING python -c "from logger import logger; logger.info('info')"` does NOT show info message
- Logging output includes proper timestamps, levels, logger names
- No sensitive data (keys, passwords) logged in any messages

**Dependencies:**
- Task 1 (requirements.txt, .env.example)
- Task 2 (config.py for environment variable access)

**Key Constraints:**
- Use Python logging module (built-in, no external logging library)
- Rich library used only for text formatting (colors and output), not for full logging
- JSON output must be valid JSON parseable by json.loads()
- Module-level logger instance must be immediately importable: `from logger import logger`
- Do not log full request/response bodies (only metadata: IDs, times, error messages)
- Text formatter must use ANSI color codes or Rich's Text class if using Rich output

---

### Task 3: Data Models Implementation (models.py)

**Objective:** Define all Pydantic schemas for request/response validation and domain models.

**Context:**
- Uses Pydantic v2 (latest, installed via requirements.txt)
- All models are used for validation by AgentOS automatically
- No custom validation logic needed beyond Pydantic defaults
- Models are imported by app.py and tests

**Requirements:**

1. Define `RecipeRequest` schema (input):
   - `ingredients: List[str]` (required)
   - `diet: Optional[str] = None` (e.g., "vegetarian", "vegan")
   - `cuisine: Optional[str] = None` (e.g., "italian", "mexican")
   - `meal_type: Optional[str] = None` (e.g., "main course", "dessert")
   - `intolerances: Optional[str] = None` (e.g., "gluten, peanuts")

2. Define `Ingredient` model (domain):
   - `name: str` (ingredient name)
   - `confidence: float` (0.0 to 1.0, from vision API)

3. Define `Recipe` model (domain):
   - `title: str` (recipe name)
   - `description: Optional[str] = None` (brief description)
   - `ingredients: List[str]` (list of ingredient names)
   - `instructions: List[str]` (step-by-step instructions)
   - `prep_time_min: int` (preparation time in minutes)
   - `cook_time_min: int` (cooking time in minutes)
   - `source_url: Optional[str] = None` (Spoonacular recipe URL)

4. Define `RecipeResponse` schema (output):
   - `recipes: List[Recipe]` (list of Recipe objects)
   - `ingredients: List[str]` (extracted/provided ingredients used)
   - `preferences: dict[str, str]` (tracked preferences: diet, cuisine, etc.)
   - `session_id: Optional[str] = None` (unique conversation identifier)
   - `run_id: Optional[str] = None` (unique interaction identifier)

5. Define `IngredientDetectionOutput` model (tool output):
   - `ingredients: List[str]` (detected ingredient names)
   - `confidence_scores: dict[str, float]` (name → confidence mapping)
   - `image_description: Optional[str] = None` (human-readable image description)

**Input:**
- None (data modeling task)

**Output:**
- `models.py` file with all Pydantic models
- Models ready to import: `from models import Recipe, RecipeRequest, RecipeResponse, etc.`

**Success Criteria:**
- All models are valid Pydantic BaseModel subclasses
- `RecipeRequest(ingredients=["tomato"])` creates object without error
- `RecipeRequest(diet="invalid")` still creates object (string validation not strict)
- `RecipeResponse` accepts all required and optional fields
- Models have proper type hints
- `python -c "from models import RecipeRequest; print(RecipeRequest.model_json_schema())"` outputs valid JSON schema

**Dependencies:**
- Task 2 (for imports only, optional)

**Key Constraints:**
- Use `Optional[X] = None` for optional fields, not `Union[X, None]`
- Use `List[X]` from typing module for list fields
- Include docstrings for each model explaining purpose
- Do not add custom validators or computed fields (keep models simple)
- All models inherit from `BaseModel`

---

### Task 4: Unit Tests - Models Validation (tests/unit/test_models.py)

**Objective:** Test Pydantic model validation for correctness.

**Context:**
- Tests should be isolated and fast (no external calls)
- Uses pytest framework
- Tests imported models from models.py
- Validates both successful and failure cases

**Requirements:**

1. Test `RecipeRequest` validation:
   - Valid request with only required fields: `ingredients=["tomato", "basil"]`
   - Valid request with optional fields: includes diet, cuisine, meal_type, intolerances
   - Invalid: missing required ingredients field (should raise ValueError)
   - Invalid: empty ingredients list (should still be valid per Pydantic)
   - Invalid: ingredients not a list (should raise ValueError)

2. Test `Recipe` model validation:
   - Valid recipe with all required fields
   - Valid recipe with optional fields (description, source_url)
   - Validate field types: `prep_time_min` and `cook_time_min` are integers

3. Test `RecipeResponse` schema validation:
   - Valid response with all fields populated
   - Valid response with optional fields as None
   - Validate nested Recipe objects in recipes list

4. Test `IngredientDetectionOutput` validation:
   - Valid output with all required fields
   - Validate confidence_scores is dict of strings to floats
   - Test with partial confidence scores (not all ingredients have scores)

5. Test JSON serialization/deserialization:
   - RecipeRequest: `model_validate_json(model.model_dump_json())` round-trips
   - RecipeResponse: Same round-trip test
   - Validate proper datetime/float handling if present

**Input:**
- models.py from Task 3
- pytest installed (from Task 1)

**Output:**
- `tests/unit/test_models.py` with all test cases

**Success Criteria:**
- `pytest tests/unit/test_models.py -v` runs and all tests pass
- At least 10 test functions
- Test both valid and invalid cases
- No external API calls (all tests isolated)
- Coverage includes all models from models.py

**Dependencies:**
- Task 3 (models.py)
- Task 1 (pytest)

**Key Constraints:**
- Use `pytest.raises(ValidationError)` for invalid case testing
- Import models from models.py, not hard-code schema definitions
- Do not mock any external services
- Keep tests focused on validation, not business logic

---

### Task 5: Unit Tests - Configuration (tests/unit/test_config.py)

**Objective:** Test configuration loading and validation.

**Context:**
- Tests should isolate environment variable behavior
- Uses pytest with monkeypatch fixture for environment variable mocking
- Tests config.py module

**Requirements:**

1. Test environment variable priority:
   - System env var overrides .env value
   - .env value used if system env var not set
   - Default value used if neither set

2. Test required fields validation:
   - Missing GEMINI_API_KEY raises ValueError
   - Missing SPOONACULAR_API_KEY raises ValueError
   - Both keys present validates without error

3. Test numeric conversions:
   - PORT converts to int (default 7777)
   - MAX_HISTORY converts to int (default 3)
   - MAX_IMAGE_SIZE_MB converts to int (default 5)
   - MIN_INGREDIENT_CONFIDENCE converts to float (default 0.7)

4. Test optional fields:
   - DATABASE_URL is optional (None if not set)
   - GEMINI_MODEL has default "gemini-1.5-flash"

5. Test .env file loading:
   - If .env exists, values are loaded
   - If .env doesn't exist, load_dotenv() doesn't raise error
   - Precedence: system env > .env > defaults

**Input:**
- config.py from Task 2
- pytest with monkeypatch fixture

**Output:**
- `tests/unit/test_config.py` with all test cases

**Success Criteria:**
- `pytest tests/unit/test_config.py -v` runs and all tests pass
- At least 8 test functions covering priority, validation, conversions
- Tests use monkeypatch to isolate environment
- No external API calls

**Dependencies:**
- Task 2 (config.py)
- Task 1 (pytest)

**Key Constraints:**
- Use pytest monkeypatch fixture for environment variable isolation
- Test required field validation by patching env vars to empty strings
- Do not actually read/write .env file in tests (use monkeypatch only)
- Keep tests fast and isolated

---

### Task 6: Ingredient Detection Pre-Hook (ingredients.py)

**Objective:** Implement image processing and ingredient extraction using Gemini vision API.

**Context:**
- This is a pre-hook function (executes before agent processes request)
- Runs locally in Python, not exposed to agent as tool
- Calls Gemini vision API once per image
- Appends results to user message as clean text
- Clears images from input to prevent agent re-processing
- Must handle errors gracefully (image processing failures)
- Uses google-generativeai library

**Requirements:**

1. Implement `extract_ingredients_pre_hook` function:
   - Signature: `extract_ingredients_pre_hook(run_input: RunInput, session=None, user_id: str = None, debug_mode: bool = None) -> None`
   - Access images via `getattr(run_input, 'images', [])`
   - Return early (None) if no images present
   - No return value needed (modifies run_input in-place)

2. For each image:
   - Get image bytes from `image.url` (HTTP/HTTPS fetch) or `image.content` (direct bytes)
   - Validate image format (JPEG or PNG only) using `imghdr.what()`
   - Validate image size: fail if > config.MAX_IMAGE_SIZE_MB
   - Return HTTP 413 error if size exceeded (via exception handling at API layer)

3. Call Gemini vision API:
   - Configure: `genai.configure(api_key=config.GEMINI_API_KEY)`
   - Create model: `genai.GenerativeModel(config.GEMINI_MODEL)`
   - Prompt: "Extract all food ingredients from this image. Return JSON with 'ingredients' list and 'confidence_scores' dict mapping ingredient name to confidence (0.0-1.0)."
   - Image input: `{"mime_type": "image/jpeg", "data": image_bytes}`

4. Parse Gemini response:
   - Extract JSON from response text
   - Expected format: `{"ingredients": [...], "confidence_scores": {"ingredient_name": 0.85, ...}}`
   - Filter ingredients by MIN_INGREDIENT_CONFIDENCE threshold
   - Keep only ingredients with confidence >= threshold

5. Append to user message:
   - Format: `f"{run_input.input_content}\n\n[Detected Ingredients] {ingredient1}, {ingredient2}, ..."`
   - Clear images from run_input: `run_input.images = []` (prevents agent re-processing)
   - Update run_input in-place

6. Error handling:
   - Log warnings (not errors) if image processing fails
   - Continue to next image on failure (resilient)
   - If all images fail and no ingredients detected, append nothing (graceful degradation)
   - No exceptions should bubble up (pre-hook should never crash)

**Input:**
- config.py from Task 2 (for API key, model name, thresholds)
- google-generativeai library (from Task 1)

**Output:**
- `ingredients.py` file with `extract_ingredients_pre_hook` function
- Ready to import: `from ingredients import extract_ingredients_pre_hook`

**Success Criteria:**
- Function signature matches Agno pre-hook contract
- Handles JPEG/PNG images, rejects other formats
- Filters by MIN_INGREDIENT_CONFIDENCE correctly
- Appends [Detected Ingredients] section to message
- Clears images from run_input
- Gracefully handles errors without crashing
- Tested manually with sample images

**Dependencies:**
- Task 2 (config.py for API key, thresholds)
- Task 1 (google-generativeai library)

**Key Constraints:**
- Must not raise exceptions (pre-hooks should be resilient)
- Must not store base64 images (only text ingredients)
- Must call Gemini vision API exactly once per image (not twice)
- Must filter by confidence threshold
- Log warnings (not errors) on failures
- JSON parsing should be lenient (handle malformed JSON gracefully)

---

### Task 7: Local Tool Implementation (Gemini Vision Integration)

**Objective:** Set up Gemini API integration for ingredient detection with retry logic.

**Context:**
- Complements Task 6 (pre-hook implementation)
- Provides helper functions for API calls with retry logic
- Handles JSON parsing and error recovery
- Used by both pre-hook (ingredients.py) and tests

**Requirements:**

1. Create helper function `fetch_image_from_url(url: str) -> bytes`:
   - Fetch image bytes from HTTP/HTTPS URL
   - Return raw bytes
   - Raise exception on network errors
   - Used by pre-hook to fetch from image.url

2. Create helper function `validate_image(image_bytes: bytes) -> None`:
   - Check format using `imghdr.what(None, h=image_bytes)`
   - Only allow JPEG and PNG
   - Raise ValueError with message: "Invalid format: {format}" if not supported
   - Check size: raise ValueError with message: "Image too large: {size}MB" if > MAX_IMAGE_SIZE_MB
   - Return None if valid (no exception means valid)

3. Create helper function `parse_json(text: str) -> dict`:
   - Extract JSON from response text
   - Handle case where response contains text before/after JSON
   - Use regex or try multiple parsing strategies
   - Return dict with 'ingredients' and 'confidence_scores' keys
   - Raise exception if JSON cannot be parsed (let caller handle)

4. Create helper function `extract_ingredients_with_retries(image_bytes: bytes, max_retries: int = 3) -> dict`:
   - Call Gemini vision API with exponential backoff retry logic
   - Retry on transient failures (network errors, rate limits, 5xx errors)
   - Backoff: 1 second, 2 seconds, 4 seconds
   - Return dict with ingredients list and confidence_scores
   - Log each retry attempt for debugging
   - Raise exception after max_retries exceeded

5. Configuration for retries:
   - MAX_RETRIES = 3 (configurable via parameter)
   - Initial delay: 1 second
   - Exponential backoff: multiply delay by 2 each retry

**Input:**
- config.py from Task 2 (for MAX_IMAGE_SIZE_MB)
- google-generativeai library (from Task 1)

**Output:**
- Helper functions in ingredients.py or separate module
- Ready to use in pre-hook and tests

**Success Criteria:**
- `validate_image()` accepts JPEG/PNG, rejects others
- `validate_image()` rejects oversized images
- `parse_json()` extracts JSON from text response
- `fetch_image_from_url()` downloads image bytes
- Retry logic handles transient failures gracefully
- Tests pass with mocked Gemini API

**Dependencies:**
- Task 2 (config.py)
- Task 6 (ingredients.py, pre-hook)
- Task 1 (libraries)

**Key Constraints:**
- Handle JSON parsing leniently (Gemini might add explanatory text)
- Log retry attempts for debugging
- Do not retry on permanent failures (invalid API key, malformed request)
- Keep retry logic generic (can be reused elsewhere)

---

### Task 8: Agno Agent Configuration & System Instructions

**Objective:** Configure Agno Agent with all orchestration settings and detailed system instructions.

**Context:**
- Agno Agent is the central intelligence orchestrating tool calls
- System instructions define agent behavior (not code)
- Configuration includes: model, database, memory, guardrails, tools
- Pre-hooks run before agent (ingredient detection)
- Tools include local @tool functions and external MCPTools

**Requirements:**

1. Create Agno Agent instance in app.py:
   ```python
   from agno.agent import Agent
   from agno.models.google import Gemini
   from agno.db.sqlite import SqliteDb
   
   agent = Agent(
       model=Gemini(...),
       db=SqliteDb(...),
       # ... other settings
   )
   ```

2. Configure Gemini model with retry settings:
   - Model ID: `config.GEMINI_MODEL` (default: gemini-1.5-flash)
   - Retries: 2 (automatic retry on failures)
   - Delay between retries: 1 second (initial)
   - Exponential backoff: True (1s → 2s → 4s)
   - This handles transient API failures gracefully

3. Configure database for session persistence:
   - Development: `SqliteDb(db_file="agno.db")`
   - Optional production: Check `config.DATABASE_URL`, use PostgreSQL if set
   - Database stores chat history, session metadata, preferences
   - Users can switch backends via environment variable only

4. Configure memory settings:
   - `add_history_to_context=True` (include chat history in agent context)
   - `num_history_runs=config.MAX_HISTORY` (keep last 3 conversation turns)
   - `enable_user_memories=True` (store preferences across sessions)
   - `enable_session_summaries=True` (auto-summarize long conversations)
   - `compress_tool_results=True` (compress after 3+ tool calls)

5. Configure structured I/O validation:
   - `input_schema=RecipeRequest` (validate incoming requests)
   - `output_schema=RecipeResponse` (validate agent responses)
   - AgentOS uses these for automatic validation

6. Register pre-hooks (run before agent executes):
   - Ingredient detection: `extract_ingredients_pre_hook`
   - Guardrails: PIIDetectionGuardrail(mask_pii=True) - optional
   - Guardrails: PromptInjectionGuardrail() - optional
   - Pre-hooks execute in order listed

7. Register tools:
   - MCPTools: `MCPTools(command="npx -y spoonacular-mcp")`
   - This is the ONLY tool registered (ingredient detection is pre-hook, not tool)
   - Tool provides: search_recipes(), get_recipe_information_bulk()

8. Write detailed system instructions (longest section):
   - Core principles: recipe-only domain, ground responses in tools
   - Ingredient sources: [Detected Ingredients], user message, history (priority order)
   - Tool usage: search_recipes() then get_recipe_information_bulk() (two-step)
   - Decision flow: Check recipe-related → check ingredients → call tools → synthesize
   - Preference extraction: Examples (vegetarian, gluten-free, italian, etc.)
   - Edge cases: Image already processed, missing ingredients, preference changes
   - Critical guardrail: NEVER invent recipe instructions without get_recipe_information_bulk()

**Input:**
- config.py from Task 2 (for settings)
- models.py from Task 3 (for schemas)
- ingredients.py from Task 6 (for pre-hook function)

**Output:**
- Agno Agent instance configured in app.py
- System instructions embedded in agent initialization

**Success Criteria:**
- Agent instance created without errors
- `python -c "from app import agent; print(agent)"` succeeds
- System instructions include all required sections
- Pre-hooks registered and called in correct order
- Tools registered with Spoonacular MCP
- Input/output schemas validated

**Dependencies:**
- Task 2 (config.py)
- Task 3 (models.py)
- Task 6 (ingredients.py)
- Task 1 (agno library)

**Key Constraints:**
- System instructions are comprehensive and detailed (200+ lines)
- Instructions guide agent behavior WITHOUT hardcoding logic
- Two-step recipe process (search then get_recipe_information_bulk) enforced in instructions
- Pre-hooks run BEFORE agent, not as tools
- Do not implement orchestration logic in code (use instructions instead)

---

### Task 9: AgentOS Application Setup (app.py Main)

**Objective:** Create the complete AgentOS application entry point.

**Context:**
- AgentOS provides REST API, Web UI, orchestration automatically
- Single entry point: `python app.py`
- No custom routes, no custom memory management needed
- Serves both REST API and Web UI simultaneously

**Requirements:**

1. Create main app.py structure:
   ```python
   from agno.agent import Agent
   from agno.os import AgentOS
   from agno.os.interfaces.agui import AGUI
   from config import config
   from models import RecipeRequest, RecipeResponse
   from ingredients import extract_ingredients_pre_hook
   # ... other imports
   
   # Configure agent (from Task 8)
   agent = Agent(...)
   
   # Create AgentOS
   agent_os = AgentOS(
       agents=[agent],
       interfaces=[AGUI(agent=agent)]
   )
   
   # Get FastAPI app
   app = agent_os.get_app()
   
   if __name__ == "__main__":
       # Serve application
       agent_os.serve(app="app:app", port=config.PORT)
   ```

2. AgentOS automatically provides:
   - REST API endpoints:
     - POST `/api/agents/chat` - send message and get response
     - GET `/api/agents/{session_id}/history` - retrieve conversation history
     - GET `/docs` - OpenAPI documentation (Swagger UI)
   - Web UI (AGUI): ChatGPT-like interface at http://localhost:PORT
   - Session management: Automatic per session_id
   - Tool lifecycle: Validates external MCPs on startup
   - Error handling: Returns appropriate HTTP status codes

3. Test startup flow:
   - Import all modules without error
   - Agent initialized with all configurations
   - AgentOS instance created
   - FastAPI app extracted
   - Can call `python app.py` without crashing (needs valid API keys in .env)

4. Serve method parameters:
   - `app="app:app"` (module path to ASGI app)
   - `port=config.PORT` (from environment or default 7777)
   - Do NOT use `reload=True` in production (causes issues with MCP lifespan)
   - In development, manually restart on code changes

**Input:**
- config.py from Task 2
- models.py from Task 3
- ingredients.py from Task 6
- Agent configuration from Task 8

**Output:**
- Complete app.py file (~150-200 lines)
- Ready to run: `python app.py`
- Serves REST API at http://localhost:7777
- Serves Web UI (AGUI) at http://localhost:7777

**Success Criteria:**
- `python app.py` starts without error (requires valid API keys in .env)
- REST API accessible at http://localhost:7777/api/agents/chat
- Web UI accessible at http://localhost:7777
- OpenAPI docs at http://localhost:7777/docs
- MCP connection validated on startup (fails if Spoonacular unreachable)
- Both REST API and Web UI serve the same agent

**Dependencies:**
- Task 2 (config.py)
- Task 3 (models.py)
- Task 6 (ingredients.py)
- Task 8 (agent configuration)

**Key Constraints:**
- Single entry point (python app.py only)
- No custom FastAPI routes (AgentOS provides them)
- No custom session management (Agno provides it)
- Do not use reload=True with MCP tools (lifespan issues)
- MCP startup validation is automatic (AgentOS handles it)

---

### Task 10: Integration Tests - End-to-End (tests/integration/test_e2e.py)

**Objective:** Test complete request-response flows with real images and MCP connections.

**Context:**
- Integration tests use Agno evals framework
- Real API calls to Gemini and Spoonacular (requires valid API keys)
- Requires sample test images in images/ folder
- Tests full conversation flows with session_id

**Requirements:**

1. Create test fixtures:
   - Load sample test images: images/sample_vegetables.jpg, images/sample_fruits.jpg, images/sample_pantry.jpg
   - Base64 encode for API requests
   - Document image contents (what ingredients are in each)

2. Test ingredient detection:
   - `test_image_to_ingredients`: Upload image, verify ingredients detected
   - Validate detection accuracy (>80% for clear images)
   - Verify confidence scores present
   - Verify [Detected Ingredients] section appears in agent context

3. Test recipe recommendation:
   - `test_image_to_recipes`: Upload image, request recipes, verify results
   - Validate recipes returned from Spoonacular
   - Verify recipe objects have title, ingredients, instructions
   - Verify prep/cook times present

4. Test conversation flow:
   - `test_multi_turn_conversation`: Same session_id across turns
   - Turn 1: "Show me vegetarian recipes"
   - Verify preferences extracted: diet=vegetarian
   - Turn 2: "What about Italian cuisine?"
   - Verify new preference added: cuisine=italian
   - Verify old preference preserved: diet=vegetarian

5. Test preference persistence:
   - `test_preference_persistence`: Preferences remembered across turns
   - User states "I'm gluten-free" in turn 1
   - Turn 2 without mentioning gluten-free
   - Verify agent still applies gluten-free filter to recipes

6. Test guardrails:
   - `test_off_topic_rejection`: Send off-topic request (e.g., "What's the weather?")
   - Verify agent refuses politely
   - Verify response indicates recipe-only domain

7. Test error handling:
   - `test_invalid_image_format`: Send non-image file or invalid base64
   - Verify appropriate error response (400 or 422)
   - `test_oversized_image`: Send image > MAX_IMAGE_SIZE_MB
   - Verify 413 error response

8. Test session management:
   - `test_session_isolation`: Two different session_ids
   - User A sets diet=vegetarian in session 1
   - User B in session 2 should not see vegetarian preference
   - Verify sessions are isolated

**Input:**
- app.py from Task 9 (complete application)
- config.py from Task 2 (for MAX_IMAGE_SIZE_MB and other thresholds)
- models.py from Task 3 (for response validation)
- Sample test images (create if not present)
- pytest and agno.evals

**Output:**
- `tests/integration/test_e2e.py` with all test cases
- Test results stored in AgentOS eval database

**Success Criteria:**
- `pytest tests/integration/test_e2e.py -v` runs all tests
- All tests pass with valid API keys configured
- At least 8 test functions
- Tests cover: ingredients, recipes, conversations, preferences, guardrails, errors
- No tests hardcode API key or sensitive data
- Response validation against RecipeResponse schema

**Dependencies:**
- Task 9 (app.py)
- Task 2 (config.py)
- Task 3 (models.py)
- Task 1 (pytest, agno)

**Key Constraints:**
- Use real API calls (not mocked) for integration tests
- Require valid GEMINI_API_KEY and SPOONACULAR_API_KEY in .env
- Tests should handle transient API failures gracefully
- Do not hardcode recipe titles or ingredient names (API results may vary)
- Use session_id to test conversation flows
- Validate responses against RecipeResponse schema

---

### Task 11: REST API Request/Response Testing (tests/integration/test_api.py)

**Objective:** Test REST API endpoints directly using curl/httpx.

**Context:**
- Tests REST API endpoints without using AGUI
- Validates HTTP status codes and response formats
- Tests image upload via base64
- Tests session_id handling

**Requirements:**

1. Create test client (using httpx or requests):
   - Base URL: http://localhost:7777
   - Tests run against live running app (started separately)

2. Test POST /api/agents/chat (main endpoint):
   - Successful request with ingredients and session_id
   - Validate response schema matches RecipeResponse
   - Validate HTTP 200 status
   - Verify session_id in response

3. Test image handling:
   - Send request with base64-encoded image
   - Verify ingredients extracted
   - Verify HTTP 200 response

4. Test validation:
   - Missing required fields: verify HTTP 400
   - Invalid JSON: verify HTTP 400
   - Off-topic request: verify HTTP 422 (guardrail triggered)
   - Oversized image: verify HTTP 413

5. Test session management:
   - Send two requests with same session_id
   - Verify conversation history preserved
   - Verify preferences applied in second request

6. Test error responses:
   - Verify error response has error type and message
   - Verify session_id preserved in error response

**Input:**
- app.py running on port 7777
- config.py for PORT setting
- models.py for response schema

**Output:**
- `tests/integration/test_api.py` with API endpoint tests

**Success Criteria:**
- All tests pass against running app
- Tests cover all HTTP status codes (200, 400, 413, 422, 500)
- Response schemas validated
- Session management tested
- At least 10 test functions

**Dependencies:**
- Task 9 (running app.py)
- Task 3 (models.py for schema)

**Key Constraints:**
- Tests require live running app (cannot be run in CI without app running)
- Use httpx or requests library for HTTP calls
- Do not modify app.py during test execution
- Validate response schema before using response data

---

### Task 12: Makefile Development Commands

**Objective:** Ensure Makefile targets execute all setup and development workflows with automatic virtual environment management.

**Context:**
- Makefile already exists (from repository setup)
- Commands needed: setup, dev, run, test, eval, clean
- Must handle Python environment isolation (venv)
- Virtual environment automatically created if missing
- All Python commands use venv Python executable
- Solves "externally-managed-environment" errors on Arch Linux and other distributions

**Requirements:**

1. Virtual Environment Management:
   - Define variables: `VENV_DIR := .venv`, `PYTHON := $(VENV_DIR)/bin/python`, `PIP := $(VENV_DIR)/bin/pip`
   - Create `venv-check` target: Create .venv using `python3 -m venv` if not present
   - All Python-based targets (dev, run, test, eval) depend on `venv-check`

2. `make setup` target:
   - Depend on `venv-check` (create venv first)
   - Upgrade pip: `$(PIP) install --upgrade pip`
   - Install dependencies: `$(PIP) install -r requirements.txt`
   - Create .env from .env.example if not present: `[ -f .env ] || cp .env.example .env`
   - Print instructions to edit .env file
   - Print required variables: GEMINI_API_KEY, SPOONACULAR_API_KEY

3. `make dev` target:
   - Depend on `venv-check`
   - Start application: `$(PYTHON) app.py`
   - Print message about Web UI URL: http://localhost:7777

4. `make run` target:
   - Depend on `venv-check`
   - Start application: `$(PYTHON) app.py`
   - (Same as dev for this implementation)

5. `make test` target:
   - Depend on `venv-check`
   - Run unit tests: `$(PYTHON) -m pytest tests/unit/ -v --tb=short`
   - Print "Running unit tests" message

6. `make eval` target:
   - Depend on `venv-check`
   - Run integration tests: `$(PYTHON) -m pytest tests/integration/ -v --tb=short`
   - Print "Running integration tests" message

7. `make clean` target:
   - Remove __pycache__ directories
   - Remove .pyc and .pyo files
   - Remove .pytest_cache and .coverage directories
   - Remove .egg-info directories
   - Print "Clean complete" message

8. `.PHONY` declaration:
   - Declare all targets as phony: setup, dev, run, test, eval, clean, help, venv-check

**Input:**
- Existing Makefile (from repository)

**Output:**
- Updated Makefile with venv support and all targets

**Success Criteria:**
- `make setup` creates .venv directory and installs all dependencies
- Virtual environment created automatically on first use
- `make dev` starts application using .venv Python
- `make test` runs unit tests using .venv Python
- `make eval` runs integration tests using .venv Python
- `make clean` removes cache files
- All targets use `.venv/bin/python` and `.venv/bin/pip` paths
- Each target prints helpful messages
- Works on Arch Linux and other systems with externally-managed-environment restrictions
- No need for manual `python3 -m venv` command

**Dependencies:**
- All previous tasks (for targets to work)

**Key Constraints:**
- Use VENV_DIR, PYTHON, and PIP variables consistently across all targets
- Virtual environment path: `.venv` (not customizable)
- Do not use `reload=True` for app.py (MCP issues)
- Include helpful messages for each target
- Use echo statements for user guidance
- All Python execution must use `$(PYTHON)` not bare `python`
- All pip usage must use `$(PIP)` not bare `pip`

---

### Task 13: Sample Test Images Preparation

**Objective:** Provide sample images for testing ingredient detection and recipe flows.

**Context:**
- Required for integration tests (Task 10)
- Should be representative of typical user inputs
- Multiple categories to test different ingredients
- Should be actual image files or described for creation

**Requirements:**

1. Create or source three sample images:
   - `images/sample_vegetables.jpg`: Clear photo of vegetables (tomatoes, basil, onions, etc.)
   - `images/sample_fruits.jpg`: Clear photo of fruits (bananas, apples, berries, etc.)
   - `images/sample_pantry.jpg`: Pantry items (pasta, beans, rice, canned goods, etc.)

2. Document image contents:
   - Create `images/README.md` describing each image
   - List expected ingredients in each image
   - Provide context for test expectations

3. Constraints:
   - Images should be JPEG or PNG format
   - Maximum 5MB each (per MAX_IMAGE_SIZE_MB default)
   - Images should be clear and well-lit
   - Multiple ingredients per image (not just one ingredient)
   - Different ingredient categories across images

**Input:**
- None (sourcing task)

**Output:**
- Three sample images in images/ folder
- `images/README.md` documenting contents and expectations

**Success Criteria:**
- All three images exist in images/ folder
- All images are JPEG or PNG format
- All images under 5MB
- Documentation provides expected ingredient lists
- Tests can successfully load and process images

**Dependencies:**
- Task 1 (images/ folder created)

**Key Constraints:**
- Images should be real photos or high-quality renderings
- Ingredients should be recognizable by vision API
- Documents ingredient expectations for test validation

---

### Task 14: README.md Documentation

**Objective:** Write comprehensive README for setup, usage, and development.

**Context:**
- README guides developers and reviewers
- Should document architecture, setup, testing, and troubleshooting
- Should include examples for both REST API and Web UI usage

**Requirements:**

1. Project Overview section:
   - Brief description of service
   - Key capabilities: image → ingredients → recipes
   - Architecture diagram (Mermaid recommended)
   - Quick start: `make setup && make dev`

2. Tech Stack section:
   - AgentOS (complete runtime)
   - Agno Agent (orchestrator)
   - Gemini vision API
   - Spoonacular recipes (MCP)
   - SQLite/PostgreSQL databases

3. Setup Instructions section:
   - `make setup` (install deps, create .env)
   - Edit .env with GEMINI_API_KEY and SPOONACULAR_API_KEY
   - Get API keys (links to Google Cloud, Spoonacular)

4. Development Workflow section:
   - `make dev` to start server
   - Access Web UI at http://localhost:7777
   - Access REST API at http://localhost:7777/api/agents/chat
   - View OpenAPI docs at http://localhost:7777/docs

5. Usage Examples section:
   - REST API curl examples:
     - Text ingredients → recipes
     - Image upload → ingredients → recipes
     - Multi-turn conversation with session_id
   - Web UI walkthrough (interactive)

6. Testing section:
   - `make test` (unit tests)
   - `make eval` (integration tests)
   - Test coverage and results

7. Configuration section:
   - Environment variables table
   - Required vs optional
   - Default values
   - Database configuration (SQLite dev, PostgreSQL prod)

8. Architecture section:
   - High-level system diagram
   - Data flow (request → ingredient detection → recipe search → response)
   - Session management and memory
   - Tool orchestration

9. Troubleshooting section:
   - Common issues and solutions
   - "Spoonacular MCP unreachable" → validation on startup fails
   - "API key invalid" → check .env file
   - "Image too large" → check MAX_IMAGE_SIZE_MB and image file size

10. API Reference section:
    - POST /api/agents/chat endpoint
    - Request schema (RecipeRequest)
    - Response schema (RecipeResponse)
    - Error codes and meanings

**Input:**
- All completed tasks (app.py, config.py, models.py, etc.)
- Architecture documentation (DESIGN.md, PRD.md)

**Output:**
- Updated README.md with all sections
- Clear, well-formatted Markdown
- Examples ready to copy/paste

**Success Criteria:**
- README covers all major topics
- Setup instructions are clear and complete
- Examples are copy-paste ready
- Architecture section helps understand system
- Troubleshooting guides help resolve common issues
- README is updated if any implementation details change

**Dependencies:**
- All previous tasks (for accurate documentation)

**Key Constraints:**
- Keep README concise but complete
- Use Mermaid diagrams instead of ASCII art
- Include API examples with real data structures
- Document all configuration options
- Provide troubleshooting for common issues

---

### Task 15: Final Validation & Success Criteria Testing

**Objective:** Comprehensive validation that implementation meets PRD requirements and success criteria.

**Context:**
- Final gate before project completion
- Validates all functional and technical requirements
- Confirms code quality and extensibility
- Validates against PRD success criteria

**Requirements:**

1. Functional Success Validation:
   - [ ] Run `make setup && make dev` successfully (requires valid API keys)
   - [ ] Access Web UI at http://localhost:7777 and send test message
   - [ ] Upload image via Web UI and verify ingredients extracted
   - [ ] Request recipes via Web UI and verify results shown
   - [ ] Test REST API: `curl -X POST http://localhost:7777/api/agents/chat ...`
   - [ ] Verify session_id persistence across multiple requests
   - [ ] Test preference persistence: Set diet=vegetarian, verify in follow-up
   - [ ] Test guardrails: Send off-topic request, verify refusal

2. Technical Success Validation:
   - [ ] `make test` passes all unit tests
   - [ ] `make eval` passes all integration tests (requires API keys)
   - [ ] Traces visible in AGUI (View Session History and Tool Calls)
   - [ ] Response times < 10 seconds typical (measure and document)
   - [ ] MCP startup validation: Stop Spoonacular, verify app fails to start
   - [ ] Single command startup: `python app.py` only (no other terminals needed)
   - [ ] OpenAPI docs accessible at http://localhost:7777/docs

3. Code Quality Validation:
   - [ ] app.py is ~150-200 lines (check with `wc -l app.py`)
   - [ ] No custom orchestration logic (inspect app.py, verify system instructions only)
   - [ ] No hardcoded secrets (grep for API keys in code)
   - [ ] Separation of concerns: config.py, models.py, ingredients.py, app.py
   - [ ] Pydantic validation on all inputs/outputs (check models.py)
   - [ ] Clear docstrings on all functions and classes
   - [ ] Error handling graceful (no uncaught exceptions)

4. Extensibility Validation:
   - [ ] Understand architecture from DESIGN.md
   - [ ] Identify where to add new tool: (MCPTools in app.py or @tool function)
   - [ ] Know how to modify behavior: (Edit system instructions in app.py)
   - [ ] Understand testing approach: (Unit tests in tests/unit/, integration in tests/integration/)
   - [ ] Know how to add preferences: (Edit system instructions, preferences captured automatically)

5. PRD Success Criteria Validation:
   - [ ] Demonstrate all in-scope functionality:
     - Image input (from file or URL)
     - Text ingredient input
     - Ingredient detection from images
     - Recipe recommendation generation
     - Preference tracking (diet, allergies, cuisines)
     - Conversation memory across turns
     - Domain boundary enforcement
   - [ ] Validate out-of-scope items are not implemented (nutritional analysis, shopping lists, etc.)

6. Documentation Validation:
   - [ ] README.md covers all major topics
   - [ ] DESIGN.md explains architecture and decisions
   - [ ] PRD documents requirements
   - [ ] IMPLEMENTATION_PLAN.md provides this task list
   - [ ] copilot-instructions.md provides development guidelines
   - [ ] Makefile commands are documented and working

7. Zero Dependencies Validation (Dev Mode):
   - [ ] No external databases required to start (SQLite built-in)
   - [ ] No Docker or separate services needed (app.py is all)
   - [ ] Clone repo → make setup → make dev should work immediately
   - [ ] Only external requirement: GEMINI_API_KEY and SPOONACULAR_API_KEY

**Input:**
- All completed tasks

**Output:**
- Completion checklist marked with results
- Any issues documented with fixes
- Final validation report

**Success Criteria:**
- All functional tests pass
- All technical tests pass
- All code quality checks pass
- All extensibility checks pass
- All PRD criteria met
- All documentation complete and accurate

**Dependencies:**
- All previous tasks completed

**Key Constraints:**
- Requires valid API keys (GEMINI_API_KEY, SPOONACULAR_API_KEY)
- Requires working internet connection (Gemini and Spoonacular APIs)
- MCP startup validation requires Spoonacular MCP reachable
- Integration tests require both APIs available
- Final validation should be thorough before marking complete

---

## Task Dependencies Graph

Here's a visual guide to task execution order:

```
Task 1 (Setup)
    ↓
    ├→ Task 2 (Config) → Task 5 (Unit Tests: Config)
    ├→ Task 3 (Models) → Task 4 (Unit Tests: Models)
    │
Task 1, 2, 3 completed
    ↓
    ├→ Task 6 (Ingredient Detection Pre-Hook)
    ├→ Task 7 (Gemini Integration / Retry Logic)
    │
Task 1, 2, 3, 6 completed
    ↓
    ├→ Task 8 (Agno Agent Configuration)
    │
Task 1, 2, 3, 6, 8 completed
    ↓
    ├→ Task 9 (AgentOS Application)
    │
Task 1, 9 completed
    ↓
    ├→ Task 10 (Integration Tests: E2E)
    ├→ Task 11 (Integration Tests: API)
    │
Task 12 (Makefile) - Can run anytime
Task 13 (Sample Images) - Can run anytime
Task 14 (README) - Can run after Task 9
Task 15 (Final Validation) - After all tasks complete
```

**Recommended Execution Order:**
1. Task 1 (Setup) - Foundation
2. Task 2 (Config) + Task 3 (Models) - Configuration and schemas
3. Task 5 (Config Tests) + Task 4 (Model Tests) - Validate schemas/config
4. Task 6 (Ingredient Pre-Hook) + Task 7 (Gemini Integration)
5. Task 8 (Agent Configuration) - Orchestration setup
6. Task 9 (AgentOS Application) - Main entry point
7. Task 13 (Sample Images) - Test data
8. Task 10 (E2E Tests) + Task 11 (API Tests) - Integration tests
9. Task 12 (Makefile) - Development commands
10. Task 14 (README) - Documentation
11. Task 15 (Final Validation) - Comprehensive testing

**Parallelizable Tasks:**
- Task 2 and Task 3 (independent)
- Task 4 and Task 5 (independent, after 2 and 3)
- Task 6 and Task 7 (mostly independent, light coupling)
- Task 10 and Task 11 (both integration tests)
- Task 12, Task 13 (independent)

---

## Execution Guidelines for Coding Agent

### Before Starting Any Task
1. Read task requirements completely
2. Understand input requirements and dependencies
3. Review success criteria
4. Note key constraints and guardrails

### During Task Execution
1. Follow the specification precisely
2. Test incrementally as you build
3. Use success criteria as validation gates
4. Log warnings/errors for debugging

### After Task Completion
1. Run success criteria checks
2. Test integration with adjacent tasks
3. Document any deviations from spec
4. Mark task complete before moving next

### Handling Ambiguity
1. Refer to DESIGN.md for architectural guidance
2. Refer to PRD.md for functional requirements
3. Refer to copilot-instructions.md for development guidelines
4. When unclear, err toward simplicity and clarity

### Common Patterns
- **Configuration:** Use environment variables with .env file (Task 2)
- **Validation:** Use Pydantic models (Task 3)
- **API Integration:** Use retry logic with exponential backoff (Task 7)
- **Testing:** Unit tests are isolated, integration tests use real APIs (Task 4, 5, 10, 11)
- **Documentation:** Update README when API changes (Task 14)

---

## Success Indicators by Phase

### Phase 1: Setup (Tasks 1-5)
- ✅ Project structure created
- ✅ Dependencies installed
- ✅ Configuration loads from environment
- ✅ Models validate correctly
- ✅ Unit tests pass

### Phase 2: Tools (Tasks 6-7)
- ✅ Gemini vision API integration works
- ✅ Ingredient extraction with confidence filtering
- ✅ Retry logic handles transient failures
- ✅ Error handling graceful

### Phase 3: Orchestration (Tasks 8-9)
- ✅ Agno Agent configured with all settings
- ✅ System instructions comprehensive
- ✅ AgentOS application starts
- ✅ Both REST API and Web UI accessible

### Phase 4: Validation (Tasks 10-15)
- ✅ Integration tests pass
- ✅ API tests pass
- ✅ All Makefile commands work
- ✅ Final validation checklist complete

---

## Context Provided to Agent (From References)

The coding agent has access to:
1. **PRD.md**: Complete functional requirements and design principles
2. **DESIGN.md**: Detailed technical design, architecture decisions, and implementation guidance
3. **.github/copilot-instructions.md**: Development guidelines, best practices, memory management

**Context NOT needed in tasks (already in references):**
- High-level architecture (documented in DESIGN.md)
- Functional requirements (documented in PRD.md)
- API specifications (documented in PRD and DESIGN)
- Agno/AgentOS best practices (documented in copilot-instructions.md)

Each task focuses on **independent implementation** while referencing these documents for architecture and requirements.

