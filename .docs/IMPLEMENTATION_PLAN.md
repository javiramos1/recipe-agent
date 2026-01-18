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
   - `execution_time_ms: int` (total execution time in milliseconds)

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

### Task 6: Ingredient Detection Core Functions (ingredients.py)

**Objective:** Implement reusable image processing and ingredient extraction using Gemini vision API.

**Context:**
- Ingredient detection can run in two modes: pre-hook or tool (configured via IMAGE_DETECTION_MODE)
- Core detection logic is **mode-agnostic** (same functions for both patterns)
- Pre-hook mode (default): Runs before agent processes request, appends ingredients to message
- Tool mode (optional): Agent calls as @tool decorator when needed, returns structured output
- Must handle errors gracefully and call Gemini vision API efficiently

**Requirements:**

1. **Core Helper Functions (reusable for both modes):**

   a. `fetch_image_bytes(image_source: str | bytes) -> Optional[bytes]`:
      - Accept URL (str) or bytes directly
      - If URL: Use urllib to fetch with 10s timeout
      - Return raw bytes if successful, None on failure
      - Log warnings on network errors (don't crash)

   b. `validate_image_format(image_bytes: bytes) -> bool`:
      - Use `filetype.guess()` to detect format
      - Accept JPEG and PNG only
      - Return True if valid, False otherwise
      - Log warning if invalid format

   c. `validate_image_size(image_bytes: bytes) -> bool`:
      - Calculate size: `len(image_bytes) / (1024 * 1024)`
      - Return True if <= config.MAX_IMAGE_SIZE_MB, False otherwise
      - Log warning if exceeds limit

   d. `parse_gemini_response(response_text: str) -> Optional[dict]`:
      - Try direct JSON parse first: `json.loads(response_text)`
      - If fails, use regex to extract JSON: `re.search(r"\{.*\}", text, re.DOTALL)`
      - Handle case where Gemini adds explanatory text
      - Return dict with keys 'ingredients' (list) and 'confidence_scores' (dict)
      - Return None if parsing fails after both attempts

   e. `extract_ingredients_from_image(image_bytes: bytes) -> Optional[dict]`:
      - Validate format and size first (skip if invalid)
      - Determine MIME type from file format
      - Create Gemini client: `genai.Client(api_key=config.GEMINI_API_KEY)`
      - Call vision API with prompt requesting JSON extraction
      - Parse response using parse_gemini_response()
      - Return dict with 'ingredients' and 'confidence_scores', or None on failure
      - Log warnings (not errors) on any failures

   f. `filter_ingredients_by_confidence(ingredients: list[str], confidence_scores: dict[str, float]) -> list[str]`:
      - Filter ingredients where score >= config.MIN_INGREDIENT_CONFIDENCE
      - Preserve order of original ingredients
      - Return filtered list

2. **Pre-Hook Function (uses core functions - Mode: pre-hook):**

   `extract_ingredients_pre_hook(run_input, session=None, user_id: str = None, debug_mode: bool = None) -> None`:
   - Check for images: `getattr(run_input, 'images', [])`
   - Return early if no images
   - For each image:
     - Get bytes from `image.url` (fetch) or `image.content` (direct)
     - Validate format and size
     - Extract ingredients using `extract_ingredients_from_image()`
     - Filter by confidence
   - Append all detected ingredients to message as text: `"[Detected Ingredients] tomato, basil, mozzarella"`
   - Clear images: `run_input.images = []` (prevents agent re-processing)
   - Must not raise exceptions (pre-hooks are resilient)

3. **Tool Function (uses core functions - Mode: tool):**

   `detect_ingredients_tool(image_data: str) -> IngredientDetectionOutput`:
   - Signature: Accepts image_data as base64 or URL string (Agno provides this)
   - Decode/fetch image bytes
   - Call core functions: validate → extract → filter
   - Return `IngredientDetectionOutput` with:
     - `ingredients`: List of detected ingredient names
     - `confidence_scores`: Dict mapping ingredient to confidence
     - `image_description`: Human-readable description of what was detected
   - Raise exception on failure (tool failures are surfaced to agent)

**Input:**
- config.py from Task 2 (for API key, model, thresholds)
- google-generativeai library (from Task 1)
- filetype library (from Task 1)

**Output:**
- `ingredients.py` file with:
  - Core helper functions (fetch_image_bytes, validate_image_format, etc.)
  - extract_ingredients_pre_hook() function
  - detect_ingredients_tool() function
- Ready to import: `from ingredients import extract_ingredients_pre_hook, detect_ingredients_tool`

**Success Criteria:**
- Core functions are modular and reusable
- Pre-hook mode works: Images → ingredients appended to message, images cleared
- Tool mode works: Image input → IngredientDetectionOutput returned
- Handles JPEG/PNG images, rejects other formats
- Filters by MIN_INGREDIENT_CONFIDENCE correctly
- Gracefully handles errors without crashing
- JSON parsing lenient (handles Gemini response variations)
- All functions tested with unit tests

**Dependencies:**
- Task 2 (config.py)
- Task 1 (google-generativeai, filetype libraries)

**Key Constraints:**
- Core functions are mode-agnostic (no references to pre-hook or tool logic)
- Pre-hook: Never raise exceptions, log warnings only
- Tool: Raise exceptions so agent can handle them
- No image bytes stored (only text ingredients in history)
- Exactly one Gemini API call per image
- Log all operations with logger (debug level for normal, warning for issues)

---

### Task 7: Ingredient Detection Retry Logic & Tool Registration

**Objective:** Add retry logic for resilient Gemini API calls and register ingredient detection tool/pre-hook based on configuration.

**Context:**
- Task 6 provides core functions and both pre-hook and tool versions
- This task adds:
  1. Retry wrapper around Gemini API calls (handles transient failures)
  2. Registration logic in app.py based on IMAGE_DETECTION_MODE config
- Both modes use the same core functions, just registered differently

**Requirements:**

1. **Retry Logic Wrapper Function (in ingredients.py):**

   `extract_ingredients_with_retries(image_bytes: bytes, max_retries: int = 3) -> Optional[dict]`:
   - Wrap `extract_ingredients_from_image()` with exponential backoff retry
   - Retry on transient failures only (network errors, rate limits, 5xx errors)
   - Do NOT retry on permanent failures (invalid API key, malformed request)
   - Backoff strategy: 1s, 2s, 4s (exponential: multiply by 2 each time)
   - Log each retry attempt with current delay
   - Return result on success or None after max_retries exceeded
   - Log final warning if all retries exhausted

2. **Configuration Validation (in config.py):**

   In Config.__init__():
   - Load: `IMAGE_DETECTION_MODE = os.getenv("IMAGE_DETECTION_MODE", "pre-hook")`
   - Validate in Config.validate():
     - Allowed values: "pre-hook" or "tool"
     - Raise ValueError if invalid value provided

   In Config class docstring, add:
   - `IMAGE_DETECTION_MODE`: "pre-hook" or "tool" (default: pre-hook)
     - "pre-hook": Extract ingredients before agent processes (faster, no agent overhead)
     - "tool": Register ingredient detection as agent @tool (more agent control)

3. **Tool Registration in app.py:**

   When creating Agno Agent:
   - Check config.IMAGE_DETECTION_MODE:
     - If "pre-hook": Call `agent.add_pre_hook(extract_ingredients_pre_hook)`
     - If "tool": Call `agent.add_tool(detect_ingredients_tool)`
   - Both modes use same core functions, different orchestration

4. **Environment Variable Documentation:**

   Update .env.example with:
   ```
   # Ingredient Detection Mode: "pre-hook" (default) or "tool"
   # - pre-hook: Faster (no extra LLM call), processes before agent
   # - tool: Agent control (visible tool call, agent decides when to call)
   IMAGE_DETECTION_MODE=pre-hook
   ```

**Input:**
- ingredients.py from Task 6 (core functions, pre-hook, tool)
- config.py from Task 2 (configuration)
- app.py (for agent registration)

**Output:**
- Updated ingredients.py with retry wrapper
- Updated config.py with IMAGE_DETECTION_MODE validation
- Updated app.py with conditional tool/pre-hook registration based on mode
- Updated .env.example with new configuration

**Success Criteria:**
- `extract_ingredients_with_retries()` handles transient failures gracefully
- Retry logic respects exponential backoff (1s, 2s, 4s)
- Pre-hook mode activates when IMAGE_DETECTION_MODE="pre-hook"
- Tool mode activates when IMAGE_DETECTION_MODE="tool"
- Invalid mode values raise ValueError during config validation
- Unit tests verify retry logic with mocked API failures
- Integration tests verify both modes work end-to-end
- All existing tests still pass

**Dependencies:**
- Task 6 (ingredients.py core functions)
- Task 2 (config.py)
- app.py (for tool registration)
- Task 1 (libraries)

**Key Constraints:**
- Retry logic only in wrapper (core functions are retry-agnostic)
- Only retry transient failures (detect 429, 500-599, network errors)
- Exponential backoff: multiply delay by 2, start at 1 second
- Pre-hook registration happens in agent configuration
- Tool registration happens when creating agent
- Both modes reuse Task 6 core functions without modification
- Configuration validation happens during app startup

---

### Task 8: Spoonacular MCP Initialization Module

**Objective:** Create SpoonacularMCP initialization class with connection validation and retry logic.

**Context:**
- Spoonacular MCP is an **external Node.js service** (runs via npx)
- Must initialize and validate connection BEFORE creating agent  
- Fail application startup if MCP unreachable
- Use exponential backoff for connection retries
- Separate module (mcp_tools/spoonacular.py) for clean separation and testability

**Requirements:**

1. **Create mcp_tools/ Package:**
   - Create `mcp_tools/__init__.py` (empty, makes it a package)
   - Create `mcp_tools/spoonacular.py` with SpoonacularMCP class

2. **SpoonacularMCP Class Structure:**

   ```python
   from agno.tools.mcp import MCPTools
   import time
   from logger import logger
   
   class SpoonacularMCP:
       """Initialize and validate Spoonacular MCP connection."""
       
       def __init__(self, api_key: str, max_retries: int = 3, retry_delays: list[int] = None):
           """
           Args:
               api_key: Spoonacular API key
               max_retries: Maximum connection retry attempts
               retry_delays: List of delays (seconds) for each retry [1, 2, 4]
           """
           self.api_key = api_key
           self.max_retries = max_retries
           self.retry_delays = retry_delays or [1, 2, 4]
       
       def initialize(self) -> MCPTools:
           """
           Initialize MCP with connection validation.
           
           Returns:
               MCPTools instance ready to use
               
           Raises:
               ValueError: If API key invalid
               ConnectionError: If cannot connect after retries
           """
   ```

3. **Initialization Logic (in initialize() method):**

   a. **API Key Validation:**
      - Check `self.api_key` is not None and not empty string
      - Raise `ValueError("SPOONACULAR_API_KEY is required")` if invalid
      - Log validation: `logger.info("Validating Spoonacular API key...")`

   b. **Connection Testing with Retries:**
      - Attempt to create MCPTools: `MCPTools(command="npx -y spoonacular-mcp", env={"SPOONACULAR_API_KEY": self.api_key})`
      - If connection fails, retry with exponential backoff
      - Retry loop (up to max_retries):
        - Log retry: `logger.warning(f"Connection failed, retrying in {delay}s... (attempt {attempt}/{max_retries})")`
        - `time.sleep(delay)`
        - Try connection again
      - After all retries exhausted: raise `ConnectionError("Failed to connect to Spoonacular MCP after {max_retries} attempts")`

   c. **Success Return:**
      - Log: `logger.info("Spoonacular MCP connected successfully")`
      - Return MCPTools instance

4. **Error Handling:**
   - Catch specific exceptions:
     - `ValueError`: Invalid API key
     - `ConnectionError`: Cannot reach MCP server
     - `Exception`: Any other initialization failure
   - Log all errors with context
   - Re-raise exceptions (caller in app.py handles startup failure)

5. **Usage Pattern (in app.py later):**

   ```python
   from mcp.spoonacular import SpoonacularMCP
   from logger import logger
   
   # Initialize before creating agent
   logger.info("Initializing Spoonacular MCP...")
   spoonacular_mcp = SpoonacularMCP(
       api_key=config.SPOONACULAR_API_KEY,
       max_retries=3,
       retry_delays=[1, 2, 4]
   )
   
   try:
       mcp_tools = spoonacular_mcp.initialize()
       logger.info("MCP ready")
   except Exception as e:
       logger.error(f"MCP initialization failed: {e}")
       raise SystemExit(1)  # Fail startup
   
   # Use mcp_tools in agent
   agent = Agent(tools=[mcp_tools], ...)
   ```

**Input:**
- config.py from Task 2 (SPOONACULAR_API_KEY)
- logger.py from Task 2.5 (structured logging)
- agno.tools.mcp.MCPTools (from agno library)

**Output:**
- `mcp_tools/__init__.py` (empty file)
- `mcp_tools/spoonacular.py` with SpoonacularMCP class
- Ready to import: `from mcp_tools.spoonacular import SpoonacularMCP`

**Success Criteria:**
- `SpoonacularMCP` class instantiates without error
- `initialize()` validates API key presence
- `initialize()` tests connection to MCP server
- Retry logic uses exponential backoff (1s, 2s, 4s)
- Connection failures retry up to max_retries times
- Successful connection returns MCPTools instance
- All failures raise appropriate exceptions with clear messages
- All steps logged (info for success, warning for retries, error for failures)
- Unit tests verify initialization logic (mocked MCPTools)

**Dependencies:**
- Task 2 (config.py with SPOONACULAR_API_KEY)
- Task 2.5 (logger.py)
- Task 1 (agno library with MCPTools)
- System: Node.js and npm (for npx command)

**Key Constraints:**
- **Must initialize BEFORE agent creation** (not during)
- **Fail-fast on startup**: Raise exception if connection fails after retries
- **No silent failures**: All errors must be logged and raised
- **Exponential backoff**: Retry delays from provided list [1, 2, 4]
- **Clean separation**: All MCP logic in mcp_tools/spoonacular.py, not app.py
- **Simple and testable**: Easy to unit test with mocked MCPTools
- **No hardcoded values**: API key, retries, delays passed as parameters

**Note on MCP Tools:**
Spoonacular MCP provides these tools (agent will call them automatically):
- `search_recipes`: Search by ingredients, dietary restrictions, cuisine, meal type
- `get_recipe_information_bulk`: Get full recipe details by IDs
- **Critical pattern**: Agent MUST call search → get_recipe_information_bulk (prevents hallucinations)

---

### Task 9: Agno Agent Configuration & System Instructions

**Objective:** Configure Agno Agent with all orchestration settings and detailed system instructions.

**Context:**
- Agno Agent is the central intelligence orchestrating tool calls
- System instructions define agent behavior (not code)
- Configuration includes: model, database, memory, guardrails, tools
- Pre-hooks run before agent (ingredient detection in pre-hook mode)
- Tools include: local ingredient detection tool (tool mode) OR external MCPTools (Spoonacular from Task 8)
- Two modes supported via `IMAGE_DETECTION_MODE` config:
  - **pre-hook mode** (default): Images processed BEFORE agent receives request
  - **tool mode**: Images processed as a tool call DURING agent execution

**Requirements:**

1. **Create Agno Agent instance in app.py:**
   ```python
   from agno.agent import Agent
   from agno.models.google import Gemini
   from agno.db.sqlite import SqliteDb
   from agno.tools import tool
   from config import config
   from ingredients import extract_ingredients_pre_hook, detect_ingredients_tool
   from mcp.spoonacular import SpoonacularMCP
   
   # Initialize MCP FIRST (fail-fast if unreachable)
   logger.info("Initializing Spoonacular MCP...")
   spoonacular_mcp = SpoonacularMCP(
       api_key=config.SPOONACULAR_API_KEY,
       timeout=10,
       retry_delays=[1, 2, 4]
   )
   try:
       mcp_tools = spoonacular_mcp.initialize()
       logger.info("MCP ready")
   except Exception as e:
       logger.error(f"MCP initialization failed: {e}")
       raise SystemExit(1)  # Fail startup
   
   # Build tools list based on configuration
   tools = [mcp_tools]  # Spoonacular MCP always included
   
   # Add ingredient detection tool if in tool mode
   if config.IMAGE_DETECTION_MODE == "tool":
       # Wrap detect_ingredients_tool with @tool decorator
       @tool
       def detect_image_ingredients(image_data: str) -> dict:
           """Extract ingredients from an uploaded image using Gemini vision API.
           
           Call this tool when a user uploads an image to detect ingredients.
           The tool returns detected ingredients with confidence scores.
           
           Args:
               image_data: Base64-encoded image string or image URL
               
           Returns:
               Dict with 'ingredients' list, 'confidence_scores' dict, and 'image_description'
           """
           return detect_ingredients_tool(image_data)
       
       tools.append(detect_image_ingredients)
   
   agent = Agent(
       model=Gemini(...),  # See requirement 2 below
       db=SqliteDb(...),   # See requirement 3 below
       tools=tools,        # Include MCP tools and optionally ingredient tool
       # ... other settings (see requirements 4-7 below)
   )
   ```

2. **Configure Gemini model with retry settings:**
   - Model ID: `config.GEMINI_MODEL` (default: gemini-1.5-flash)
   - Retries: 2 (automatic retry on failures)
   - Delay between retries: 1 second (initial)
   - Exponential backoff: True (1s → 2s → 4s)
   - This handles transient API failures gracefully
   ```python
   model=Gemini(
       id=config.GEMINI_MODEL,
       api_key=config.GEMINI_API_KEY,
   )
   ```

3. **Configure database for session persistence:**
   - Development: `SqliteDb(db_file="agno.db")`
   - Optional production: Check `config.DATABASE_URL`, use PostgreSQL if set
   - Database stores chat history, session metadata, preferences
   - Users can switch backends via environment variable only
   ```python
   from agno.db.sqlite import SqliteDb
   from agno.db.postgres import PostgresDb
   
   if config.DATABASE_URL:
       db = PostgresDb(db_url=config.DATABASE_URL)
   else:
       db = SqliteDb(db_file="agno.db")
   ```

4. **Configure memory settings:**
   - `add_history_to_context=True` (include chat history in agent context)
   - `num_history_runs=config.MAX_HISTORY` (keep last 3 conversation turns)
   - `enable_user_memories=True` (store preferences across sessions)
   - `enable_session_summaries=True` (auto-summarize long conversations)
   - `compress_tool_results=True` (compress after 3+ tool calls)
   ```python
   agent = Agent(
       # ... model, db, tools ...
       add_history_to_context=True,
       num_history_runs=config.MAX_HISTORY,
       enable_user_memories=True,
       enable_session_summaries=True,
       compress_tool_results=True,
   )
   ```

5. **Configure structured I/O validation:**
   - `input_schema=RecipeRequest` (validate incoming requests)
   - `output_schema=RecipeResponse` (validate agent responses)
   - AgentOS uses these for automatic validation
   ```python
   from models import RecipeRequest, RecipeResponse
   
   agent = Agent(
       # ...
       input_schema=RecipeRequest,
       output_schema=RecipeResponse,
   )
   ```

6. **Register pre-hooks (run before agent executes):**
   - Pre-hooks execute in order listed
   - **Pre-hook mode (default)**: Register ingredient detection pre-hook
     - Extracts ingredients from images BEFORE agent processes request
     - Images converted to text and appended to message
     - Images cleared from input
   - **Tool mode**: Skip ingredient extraction pre-hook (agent calls tool instead)
   ```python
   # Conditionally add pre-hook based on mode
   pre_hooks = []
   
   if config.IMAGE_DETECTION_MODE == "pre-hook":
       # Pre-hook extracts ingredients before agent processes request
       pre_hooks.append(extract_ingredients_pre_hook)
   
   # Optional: Add guardrails
   from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
   
   pre_hooks.extend([
       PIIDetectionGuardrail(mask_pii=True),
       PromptInjectionGuardrail(),
   ])
   
   agent = Agent(
       # ...
       pre_hooks=pre_hooks,
   )
   ```

7. **Register tools (MCPTools + conditional ingredient tool):**
   - **Pre-hook mode**: Only MCPTools (Spoonacular) registered
   - **Tool mode**: MCPTools + ingredient detection tool registered
   - Agent calls tools automatically based on system instructions and user requests
   ```python
   # See requirement 1 above for complete setup
   tools = [mcp_tools]  # Spoonacular MCP always included
   
   if config.IMAGE_DETECTION_MODE == "tool":
       @tool
       def detect_image_ingredients(image_data: str) -> dict:
           """Extract ingredients from uploaded image."""
           return detect_ingredients_tool(image_data)
       
       tools.append(detect_image_ingredients)
   
   agent = Agent(
       # ...
       tools=tools,
   )
   ```

8. **Write detailed system instructions (longest section):**
   The system instructions guide agent behavior and should include:
   
   **a) Core Principles:**
   - Recipe-focused domain: Only answer recipe-related questions
   - Ground all responses in tool outputs: No hallucinated ingredients or recipes
   - Use tool results verbatim: Do not modify or invent recipe details
   
   **b) Ingredient Sources (Priority Order):**
   - Check for `[Detected Ingredients]` in message (from pre-hook or memory)
   - Fall back to user message if no detected ingredients
   - Use conversation history as context for preferences
   
   **c) Two-Step Recipe Process (Critical):**
   - NEVER provide full recipe instructions without calling `get_recipe_information_bulk`
   - Step 1: Call `search_recipes` with detected ingredients and filters
   - Step 2: Call `get_recipe_information_bulk` with returned recipe IDs to get full details
   - This two-step process prevents hallucinations
   
   **d) Decision Flow:**
   - Is user asking recipe-related question? → Proceed to check for ingredients
   - Do we have ingredients (detected or provided)? → Call search_recipes
   - Do we have recipe search results? → Call get_recipe_information_bulk for full details
   - Synthesize response from tool outputs
   
   **e) Preference Extraction:**
   - Extract and remember user preferences: dietary (vegetarian, gluten-free, vegan), cuisine (Italian, Asian), meal type (breakfast, dinner)
   - Apply preferences as filters to search_recipes tool
   - Store preferences for future conversations
   
   **f) Tool Behavior (Recipe Search):**
   - `search_recipes(ingredients, diet=None, cuisine=None, type=None)`: Search for recipes
   - Always include detected/provided ingredients in search
   - Apply user preferences as optional filters
   - `get_recipe_information_bulk(ids, add_recipe_information=True)`: Get full recipe details
   - Call ONLY AFTER search_recipes returns IDs
   - Include cooking instructions, nutritional info, time estimates
   
   **g) Image Handling (Based on Mode):**
   - **Pre-hook mode**: "[Detected Ingredients]" text already in message
     - Do NOT ask user to re-upload or describe ingredients
     - Proceed directly with recipe search
   - **Tool mode**: Call "detect_image_ingredients" tool when user uploads image
     - Agent has visibility into image processing
     - Can ask clarifying questions about detected ingredients
   
   **h) Edge Cases:**
   - No ingredients detected: Ask user to provide ingredients or try different image
   - No recipes found: Clarify what they're looking for, offer to broaden search
   - User modifies preferences mid-conversation: Update preferences and re-search
   - Multiple similar recipes: Show top 3-5 with key differences highlighted
   
   **i) Critical Guardrails:**
   - NEVER invent ingredient lists (use detected or user-provided only)
   - NEVER make up recipe instructions (use get_recipe_information_bulk only)
   - NEVER claim tool was called if it wasn't (be transparent about process)
   - If error occurs: Log it, explain to user, suggest alternative approach
   
   **Example System Instructions Template:**
   ```
   You are a professional recipe recommendation assistant. Your role is to help users discover and prepare delicious recipes based on their available ingredients and dietary preferences.
   
   ## Core Responsibility
   - Recommend recipes based on detected or provided ingredients
   - Provide complete recipe details with instructions, cooking time, and nutritional info
   - Remember and apply user preferences (dietary, cuisine, meal type)
   - Help users refine searches and explore variations
   
   ## Ingredient Sources (Use in Order)
   1. [Detected Ingredients] in user message (from image pre-processing)
   2. Ingredients mentioned in current message
   3. Previous ingredients mentioned in conversation history
   
   ## Recipe Search Process (Two Steps Required)
   IMPORTANT: You MUST follow this process every time:
   
   Step 1: Call search_recipes
   - Input: Use detected or provided ingredients
   - Filters: Apply user preferences (diet, cuisine, type)
   - Extract recipe IDs from results
   
   Step 2: Call get_recipe_information_bulk
   - Input: Recipe IDs from Step 1
   - Always set add_recipe_information=True
   - This gives you full instructions, time, and nutrition data
   
   NEVER provide recipe instructions without completing Step 2.
   
   ## Image Handling
   [Include mode-specific instructions based on config]
   
   Pre-hook Mode:
   - Images are pre-processed and ingredients appended to your message
   - You'll see "[Detected Ingredients] ..." in the message
   - Proceed directly with recipe search (do NOT re-process)
   
   Tool Mode:
   - If user uploads an image, call detect_image_ingredients tool
   - Review detected ingredients with the user
   - Ask clarifying questions if needed
   - Then proceed with recipe search
   
   ## Preference Management
   - Extract preferences from user messages (e.g., "I'm vegetarian", "I like Italian food")
   - Store preferences automatically (they persist across conversations)
   - Always apply stored preferences when searching recipes
   - Ask before changing preferences mid-conversation
   
   ## Response Guidelines
   - Be conversational and friendly
   - Show top 3-5 most relevant recipes
   - Highlight key differences (calories, prep time, difficulty)
   - Link to full recipe details
   - Ask follow-up questions to refine search if needed
   ```

**Input:**
- config.py from Task 2 (for settings, IMAGE_DETECTION_MODE)
- models.py from Task 3 (for schemas)
- ingredients.py from Task 6 (for pre-hook and tool functions)
- mcp/spoonacular.py from Task 8 (SpoonacularMCP class)

**Output:**
- Agno Agent instance configured in app.py with all settings
- System instructions embedded in agent initialization (~200-300 lines)
- Conditional tool/pre-hook registration based on IMAGE_DETECTION_MODE
- Proper error handling and logging

**Success Criteria:**
- Agent instance created without errors
- `python -c "from app import agent; print(agent)"` succeeds
- System instructions include all sections (a-i above)
- Pre-hooks registered correctly (pre-hook mode only)
- Ingredient tool registered correctly (tool mode only)
- Spoonacular MCP tools registered and available
- Input/output schemas validated
- Both modes work end-to-end in tests

**Dependencies:**
- Task 2 (config.py with IMAGE_DETECTION_MODE)
- Task 3 (models.py for schemas)
- Task 6 (ingredients.py with pre-hook and tool functions)
- Task 8 (mcp/spoonacular.py with SpoonacularMCP initialization)
- Task 1 (agno library with Agent, @tool decorator)

**Key Constraints:**
- System instructions are comprehensive and detailed (200-300 lines)
- Instructions guide agent behavior WITHOUT hardcoding orchestration logic
- Two-step recipe process (search then get_recipe_information_bulk) MUST be enforced in instructions
- Pre-hooks run BEFORE agent (pre-hook mode only)
- Ingredient tool registered as @tool decorator (tool mode only)
- Conditional logic based on IMAGE_DETECTION_MODE configuration
- Do not implement orchestration logic in code (use instructions instead)
- MCP must be initialized BEFORE agent creation (Task 8 provides initialized MCPTools)
- Ingredient tool must return consistent dict format: `{"ingredients": [...], "confidence_scores": {...}, "image_description": "..."}`

---

### Task 10: AgentOS Application Setup with Factory Pattern

**Objective:** Create the complete AgentOS application entry point using factory pattern for modular agent initialization.

**Context:**
- AgentOS provides REST API, Web UI, orchestration automatically
- Single entry point: `python app.py`
- Factory pattern separates concerns into modular files: agent.py, prompts.py, hooks.py
- MCP must be initialized BEFORE agent creation (fail-fast on startup)
- No custom routes or memory management needed (AgentOS handles automatically)

**Requirements:**

1. **Create agent.py** (~150 lines) - Agent Factory Function:
   - Export `initialize_recipe_agent() -> Agent` factory function
   - 5-step initialization process:
     - Step 1: Initialize SpoonacularMCP with connection validation (fail-fast if unreachable)
     - Step 2: Configure database (SQLite for dev, PostgreSQL for production via DATABASE_URL)
     - Step 3: Register tools (Spoonacular MCP + optional ingredient detection tool based on IMAGE_DETECTION_MODE)
     - Step 4: Register pre-hooks (from hooks.py factory)
     - Step 5: Configure Agno Agent with all settings
   - Return fully configured Agent instance ready for AgentOS
   - Log each initialization step with appropriate levels
   - Handle all errors gracefully with clear error messages

2. **Create prompts.py** (~800 lines) - System Instructions Constant:
   - Export `SYSTEM_INSTRUCTIONS` constant (pure data, no logic)
   - Comprehensive behavior definition for agent covering:
     - Core responsibilities and domain boundaries
     - Ingredient sources (detected → user message → history)
     - Two-step recipe process (search_recipes → get_recipe_information_bulk)
     - Image handling (pre-hook vs tool mode)
     - Preference extraction and persistence
     - Tool usage guidance
     - Edge cases and fallback strategies
     - Critical guardrails (no hallucinations, no invented recipes)

3. **Create hooks.py** (~30 lines) - Pre-Hooks Factory:
   - Export `get_pre_hooks() -> List` factory function
   - Return list of pre-hooks based on configuration:
     - If IMAGE_DETECTION_MODE == "pre-hook": Include extract_ingredients_pre_hook
     - Always include guardrails (PromptInjectionGuardrail)
   - No logging side effects during factory call

4. **Update app.py** (~50 lines) - Minimal Orchestration:
   - Import factory: `from agent import initialize_recipe_agent`
   - Call factory: `agent = initialize_recipe_agent()`
   - Create AgentOS instance with agent and AGUI interface
   - Extract FastAPI app: `app = agent_os.get_app()`
   - Serve on configured port with `reload=False` (production-ready)
   - Log startup message with URLs for Web UI, API, and docs
   - No MCP logic or initialization in app.py (delegated to agent.py factory)

5. **Register with AgentOS:**
   - Pass initialized agent to AgentOS constructor
   - Register AGUI interface for Web UI
   - Both REST API and Web UI serve same agent instance
   - AgentOS automatically exposes: REST endpoints, Web UI, OpenAPI docs

**Input (Dependencies):**
- config.py from Task 2 (configuration settings and validation)
- logger.py from Task 2.5 (structured logging)
- models.py from Task 3 (Pydantic schemas: RecipeRequest, RecipeResponse)
- ingredients.py from Task 6 (extract_ingredients_pre_hook, detect_ingredients_tool functions)
- mcp_tools/spoonacular.py from Task 8 (SpoonacularMCP class with connection validation)
- hooks.py from Task 9 (get_pre_hooks factory)
- All libraries from Task 1 (agno, google-generativeai, pydantic, etc.)

**Output:**
- `app.py` (~50 lines): Minimal orchestration, AgentOS entry point
- `agent.py` (~150 lines): initialize_recipe_agent() factory function
- `prompts.py` (~800 lines): SYSTEM_INSTRUCTIONS constant
- `hooks.py` (~30 lines): get_pre_hooks() factory function
- All files ready for import and use

**Success Criteria:**
- `python app.py` starts without errors
- REST API accessible at http://localhost:7777/api/agents/chat
- Web UI (AGUI) accessible at http://localhost:7777
- OpenAPI docs at http://localhost:7777/docs
- MCP connection validated on startup (fails application if unreachable)
- Both REST API and Web UI serve same agent instance
- Factory pattern maintains clean separation of concerns
- All 140 unit tests still pass after implementation
- No hardcoded values (all use config module)
- Comprehensive logging throughout initialization

**Key Constraints:**
- app.py must be minimal (~50 lines, no logic)
- MCP initialization must happen in agent.py, not app.py
- All behavior defined in system instructions (prompts.py), not code
- Pre-hooks and tools registered via factories (not hardcoded in app.py)
- No custom API routes (AgentOS provides all endpoints automatically)
- No custom memory management (Agno handles automatically)
- reload=False for production readiness (not reload=True)
- Factory functions must be idempotent and handle errors gracefully
- All initialization logged with logger (debug/info for normal flow, warning/error for issues)

---


### Task 12: Integration Tests - End-to-End (tests/integration/test_e2e.py)

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
- app.py from Task 11 (complete application)
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
- Task 11 (app.py)
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

### Task 13: REST API Request/Response Testing (tests/integration/test_api.py)

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
- Task 11 (running app.py)
- Task 3 (models.py for schema)

**Key Constraints:**
- Tests require live running app (cannot be run in CI without app running)
- Use httpx or requests library for HTTP calls
- Do not modify app.py during test execution
- Validate response schema before using response data

---

### Task 14: Makefile Development Commands

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

### Task 15: Sample Test Images Preparation

**Objective:** Provide sample images for testing ingredient detection and recipe flows.

**Context:**
- Required for integration tests (Task 12)
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

### Task 16: README.md Documentation

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

### Task 17: Final Validation & Success Criteria Testing

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
    ├→ Task 6 (Ingredient Detection Core Functions)
    ├→ Task 7 (Retry Logic & Tool Registration)
    │
Task 1, 2, 3, 6, 7 completed
    ↓
    ├→ Task 8 (Spoonacular MCP Integration) - CRITICAL EXTERNAL TOOL
    │
Task 1, 2, 3, 6, 7, 8 completed
    ↓
    ├→ Task 9 (Agno Agent Configuration)
    │
Task 1, 2, 3, 6, 7, 8, 9 completed
    ↓
    ├→ Task 10 (AgentOS Application)
    │
Task 10 completed
    ↓
    ├→ Task 11 (Integration Tests: E2E)
    ├→ Task 12 (Integration Tests: API)
    │
Task 13 (Makefile) - Can run anytime
Task 14 (Sample Images) - Can run anytime
Task 15 (README) - Can run after Task 10
Task 16 (Final Validation) - After all tasks complete
```

**Recommended Execution Order:**
1. Task 1 (Setup) - Foundation
2. Task 2 (Config) + Task 3 (Models) - Configuration and schemas
3. Task 5 (Config Tests) + Task 4 (Model Tests) - Validate schemas/config
4. Task 6 (Ingredient Detection Core) + Task 7 (Retry Logic)
5. Task 8 (Spoonacular MCP Integration) - **CRITICAL: External recipe tool**
6. Task 9 (Agent Configuration) - Orchestration setup
7. Task 10 (AgentOS Application) - Main entry point
8. Task 14 (Sample Images) - Test data
9. Task 11 (E2E Tests) + Task 12 (API Tests) - Integration tests
10. Task 13 (Makefile) - Development commands
11. Task 15 (README) - Documentation
12. Task 16 (Final Validation) - Comprehensive testing

**Parallelizable Tasks:**
- Task 2 and Task 3 (independent)
- Task 4 and Task 5 (independent, after 2 and 3)
- Task 6 and Task 7 (mostly independent, light coupling)
- Task 11 and Task 12 (both integration tests)
- Task 13, Task 14 (independent)

---

## Summary of Tasks

**Total Tasks: 17**

**Foundation Tasks (1-5):**
- Task 1: Project Structure & Dependencies
- Task 2: Configuration Management (config.py)
- Task 3: Pydantic Data Models (models.py)
- Task 4: Unit Tests - Models
- Task 5: Unit Tests - Configuration

**Core Features (6-8):**
- Task 6: Ingredient Detection Core Functions (ingredients.py)
- Task 7: Ingredient Detection Retry Logic & Tool Registration
- Task 8: **Spoonacular MCP Integration & Configuration** (NEW - CRITICAL)

**Orchestration & Application (9-10):**
- Task 9: Agno Agent Configuration & System Instructions (renumbered from 8)
- Task 10: AgentOS Application Setup (renumbered from 9)

**Testing & Validation (11-12):**
- Task 11: Integration Tests - End-to-End (renumbered from 10)
- Task 12: REST API Request/Response Testing (renumbered from 11)

**Development & Documentation (13-16):**
- Task 13: Makefile Development Commands (renumbered from 12)
- Task 14: Sample Test Images Preparation (renumbered from 13)
- Task 15: README.md Documentation (renumbered from 14)
- Task 16: Final Validation & Success Criteria Testing (renumbered from 15)

**Key Addition:**
- **Task 8 (NEW)**: Spoonacular MCP Integration - External recipe search tool
  - Clarifies this is external (via npx, not local code)
  - Explains MCP server command and configuration
  - Documents available tools (search_recipes, get_recipe_information_bulk)
  - Describes two-step recipe pattern (search → get details)
  - Covers startup validation requirements
  - No mcp/ folder needed (runs externally)

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

