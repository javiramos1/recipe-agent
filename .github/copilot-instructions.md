# Copilot Instructions - Recipe Recommendation Service

**Code Challenge Project: Production-Quality GenAI System**

## ⚡ CRITICAL - Read First

**Before implementing any task:**
1. **Query Context7 MCP** for latest library documentation
2. **Code like a human**: Direct, clean, concise - no verbose comments or over-engineered code
3. **Production-ready only**: Error handling, type hints, async I/O, proper resource cleanup
4. **Tests after every change**: Add unit tests, keep them simple and minimal, run `make test`
5. **Use environment variables** for ALL configuration (no hardcoded values)
6. **Use logger in every file**: `from logger import logger` - structured logging everywhere
7. **Rolling status in instructions**: Update copilot-instructions.md status after each task
8. **README as final snapshot**: README.md represents current state (not rolling updates)
9. **⚠️ ASYNC/AWAIT REQUIRED - ALL I/O OPERATIONS**: 
   - Network calls: `aiohttp` (not `urllib`, `requests`)
   - Sleep/delays: `asyncio.sleep()` (not `time.sleep()`)
   - All functions doing I/O: `async def` with `await`
   - Sync APIs: Wrap with `asyncio.to_thread()` to prevent blocking
   - No `time.sleep()`, `urllib`, or sync blocking calls anywhere
10. **Never log sensitive data**: No API keys, passwords, images, or PII in logs
11. **Commit and push after each task**: `git add -A`, `git commit -m "Task [N]: description"`, `git push origin main`
12. **Follow Do's & Don'ts strictly** (see below)
13. **Always update this file status section** after completing each task
14. **Always use makefile commands** for setup, dev, test, eval, run, clean. Do not use python app.py directly.

**Critical Architecture Patterns:**
11. **Pre-hook pattern**: Images processed BEFORE agent executes. Extract ingredients → append as text → clear images from input. Agent only sees ingredient text.
12. **MCP initialization pattern**: SpoonacularMCP class validates connection BEFORE agent creation. Exponential backoff retries (1s → 2s → 4s). Fail startup if unreachable.
13. **Two-step recipe process**: NEVER generate recipe instructions without calling `get_recipe_information_bulk`. Always: search_recipes → get_recipe_information_bulk (prevents hallucinations).
14. **Never store images**: Base64/image bytes NEVER in memory or database. Only ingredient TEXT in chat history.
15. **System instructions define behavior, NOT code**: Orchestration logic goes in Agno system instructions, not Python code. Let Agno handle tool routing, memory, retries.
16. **Single entry point**: Everything runs from `python app.py`. No separate servers or multiple terminals.
17. **No custom code for**: Orchestration logic, API routes, memory management, session storage. AgentOS/Agno provide these automatically.
18. **MCP validation at startup only**: External MCPTools (Spoonacular) need startup validation via SpoonacularMCP class. Local @tool functions don't need validation.
19. **Agno handles automatically**: Memory, retries with exponential backoff, guardrails, context compression, preference extraction. Don't implement these manually but do use Agno AI features.

## Project Overview

This is a code challenge implementing a production-quality GenAI system that transforms ingredient images into recipe recommendations using modern orchestration patterns (AgentOS, Agno Agent, MCP). The service demonstrates best practices in system design, testing, and implementation.

**Core Value Proposition:** Single-command startup (`python app.py`) providing REST API + Web UI + stateful conversational agent with automatic memory, retries, and guardrails.

## Status Section

**Current Status: Phase 2 complete with async refactoring (Tasks 1-10), 140 unit tests passing, Task 18 complete**

### Phase 1: Foundational (Tasks 1-5 + Task 2.5 logger) ✅
- [x] Task 1: Project structure, dependencies, .gitignore
- [x] Task 2: Configuration management (config.py)
- [x] Task 2.5: Logging infrastructure (logger.py)
- [x] Task 3: Data models (models.py)
- [x] Task 4: Unit tests - Models
- [x] Task 5: Unit tests - Configuration

### Phase 2: Core Features (Tasks 6-10) ✅
- [x] Task 6: Ingredient detection core (ingredients.py)
- [x] Task 7: Retry logic & tool registration
- [x] Task 8: Spoonacular MCP initialization (mcp_tools/spoonacular.py)
- [x] Task 9: Agno agent configuration & system instructions
- [x] Task 10: AgentOS application setup (app.py + AGUI)
- [x] **REFACTOR**: Factory pattern implementation `initialize_recipe_agent()` factory
- [x] **ASYNC REFACTOR** (date: 2026-01-19) All functions async

### Phase 3: Developer Tools & Testing (Tasks 11-18)
- [x] Task 18 complete (date: 2026-01-19) - Ad hoc query command
- [ ] Task 11: Integration Tests E2E - Pending
- [ ] Task 12: REST API Testing - Pending
- [x] Task 13 complete (date: 2026-01-18) - Makefile with all development commands
- [ ] Task 14: Sample Test Images - Pending
- [x] Task 15 complete (date: 2026-01-18) - Comprehensive README.md
- [ ] Task 16: Final Validation - Pending

**Update Protocol:** After completing each task, update this status section with:
- [x] Task [N] complete (date: YYYY-MM-DD) - Description of what was completed
- [ ] Next task status and what's pending

## Quick Start

1. **Read full context** (in order):
   - .docs/PRD.md - Functional requirements and success criteria
   - .docs/DESIGN.md - Architecture, design decisions, data flows (includes logger.py design)
   - .docs/IMPLEMENTATION_PLAN.md - 16 independent tasks with full specifications (includes Task 2.5: logger.py)

2. **Setup and run**:
   ```bash
   make setup    # Install deps, create .env
   make dev      # Start: python app.py
   ```

3. **Key entry points**:
   - REST API: POST http://localhost:7777/api/agents/chat
   - Web UI: http://localhost:7777
   - OpenAPI docs: http://localhost:7777/docs

## Core Architecture

Single-entry-point application (`python app.py`) with factory pattern separation:

**Initialization Flow:**
- **app.py** (~50 lines): Calls `initialize_recipe_agent()` factory → creates AgentOS → serves
- **agent.py** (~150 lines): `initialize_recipe_agent()` factory with 5 steps:
  1. MCP init: SpoonacularMCP().initialize() (validate API key, test connection, exponential backoff)
  2. DB config: SQLite (dev) or PostgreSQL (prod)
  3. Tools registration: Spoonacular MCP + optional ingredient tool
  4. Pre-hooks: From `get_pre_hooks()` (ingredient extraction + guardrails)
  5. Agent config: Gemini model, database, memory, system instructions
- **prompts.py** (~800 lines): `SYSTEM_INSTRUCTIONS` constant (pure data, no logic)
- **hooks.py** (~30 lines): `get_pre_hooks()` factory (ingredient extraction + guardrails)

**Components:**
- **AgentOS** (runtime): REST API, Web UI, MCP lifecycle, built-in tracing
- **Agno Agent** (orchestrator): Stateful memory, automatic retries, tool routing, guardrails
- **Pre-hook** (ingredients.py): Vision API integration → ingredient extraction → request enrichment
- **Spoonacular MCP** (mcp_tools/spoonacular.py): Connection validation, exponential backoff retries
- **External Recipe API** (via npx): Recipe search with filtering

**Data Flow:**
Request → Pre-hook (image processing) → Agent (orchestration) → MCP (recipe search) → Response

**MCP Initialization (Startup):**
SpoonacularMCP.initialize() → Validate API key → Test connection (retry 1s/2s/4s) → Return MCPTools → Agent creation

## Key Principles

**Architecture & Design:**
- Single entry point: `python app.py` (minimal 50-line orchestration)
- Factory pattern: Agent initialization in agent.py, not app.py
- System instructions define behavior, not code (in prompts.py)
- No custom orchestration logic (Agno handles it)
- No custom memory management (Agno automatic session persistence)
- No custom API routes (AgentOS provides REST/Web UI automatically)
- Pre-hook pattern eliminates LLM round-trip (image → ingredients → message in one call)
- Images never stored in memory (only ingredient text in chat history)
- MCP startup validation (fail startup if external tools unreachable)

**Code Quality & Operations:**
- Concise, direct, production-ready code (no verbose comments, only essential documentation)
- Python best practices (type hints, async operations, proper error handling)
- Comprehensive logging (structured, debug-friendly, no sensitive data)
- Automatic retries with exponential backoff (1s → 2s → 4s for transient failures)
- Always async where possible (async/await for I/O operations)

## Tech Stack

**Core Runtime & Orchestration:**
- **AgentOS**: Complete application runtime providing REST API, Web UI (AGUI), MCP lifecycle, built-in tracing
- **Agno Agent**: Stateful orchestrator with built-in session memory, automatic retries, structured validation
- **Gemini 1.5 Flash**: Vision API for ingredient detection from images

**Data & Storage:**
- **SQLite + LanceDB**: File-based session storage and memory (development default, zero setup)
- **PostgreSQL + pgvector**: Optional production database (configured via DATABASE_URL)

**Tools & Integration:**
- **Spoonacular MCP**: External Node.js service providing recipe search (via npx, no checkout)
- **python-dotenv**: Environment variable management with .env file support

**Testing & Quality:**
- **pytest**: Unit and integration testing framework
- **Pydantic**: Input/output validation with OpenAPI schema generation
- **aiohttp**: Async HTTP client for URL-based image fetching


## Async/Await Implementation Standards

**CRITICAL: All I/O operations MUST be async. No exceptions.**

### Network Operations

```python
# ✅ CORRECT: Async HTTP client
import aiohttp

async def fetch_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return await resp.read()

# ❌ WRONG: Synchronous urllib
import urllib.request
with urllib.request.urlopen(url) as resp:
    return resp.read()

# ❌ WRONG: Synchronous requests library
import requests
return requests.get(url).content
```

### Delays and Retries

```python
# ✅ CORRECT: Async sleep
import asyncio
await asyncio.sleep(delay_seconds)

# ❌ WRONG: Synchronous sleep (blocks event loop)
import time
time.sleep(delay_seconds)
```

### Wrapping Synchronous APIs

For third-party libraries that only provide sync APIs (Gemini client, MCPTools):

```python
# ✅ CORRECT: Use asyncio.to_thread() to prevent blocking
result = await asyncio.to_thread(sync_function, arg1, arg2)

# ✅ CORRECT: Inline with to_thread
response = await asyncio.to_thread(
    client.models.generate_content,
    model=config.GEMINI_MODEL,
    contents=[...],
)

# ❌ WRONG: Call sync function directly in async function
response = client.models.generate_content(...)  # Blocks event loop!
```

### Pre-Hook and Tool Functions

```python
# ✅ CORRECT: Async pre-hook
async def extract_ingredients_pre_hook(run_input, session=None, user_id=None, debug_mode=None):
    # All I/O is awaited
    image_bytes = await fetch_image_bytes(image_url)
    result = await extract_ingredients_from_image(image_bytes)
    # ... process result ...

# ✅ CORRECT: Async tool function
async def detect_ingredients_tool(image_data: str) -> dict:
    image_bytes = await fetch_image_bytes(image_data)
    result = await extract_ingredients_with_retries(image_bytes)
    return result

# ❌ WRONG: Sync pre-hook or tool
def extract_ingredients_pre_hook(run_input, ...):
    # Can't await here!
    image_bytes = fetch_image_bytes(...)  # Blocks!
```

### Factory Functions

```python
# ✅ CORRECT: Async factory at module level
async def initialize_recipe_agent() -> Agent:
    mcp_tools = await spoonacular_mcp.initialize()
    # ... more initialization ...
    return agent

# In app.py at startup:
agent = asyncio.run(initialize_recipe_agent())

# ❌ WRONG: Sync factory calling async MCP init
def initialize_recipe_agent() -> Agent:
    mcp_tools = spoonacular_mcp.initialize()  # Can't await in sync function!
```

### Retry Logic

```python
# ✅ CORRECT: Non-blocking exponential backoff
async def extract_with_retries(image_bytes, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await extract_ingredients_from_image(image_bytes)
            if result:
                return result
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff
                await asyncio.sleep(delay)  # Non-blocking!
    return None

# ❌ WRONG: Blocking retry delays
import time
for attempt in range(max_retries):
    try:
        result = extract_ingredients_from_image(image_bytes)
        if result:
            return result
    except Exception:
        time.sleep(2 ** attempt)  # Blocks entire app!
```

### Summary

- **Every function doing I/O**: Mark as `async def`, use `await` for I/O
- **Network fetch**: Use `aiohttp`, not `urllib` or `requests`
- **Delays**: Use `asyncio.sleep()`, never `time.sleep()`
- **Sync APIs**: Wrap with `asyncio.to_thread(sync_func, args)`
- **Startup**: Use `asyncio.run(async_factory())` at module level only
- **Never mix**: Don't call sync I/O in async functions without `to_thread()`




```
app.py              # AgentOS entry point (~50 lines, minimal orchestration)

src/                # All application code organized by function
├── __init__.py     # Package marker
├── utils/
│   ├── __init__.py
│   ├── config.py           # Environment variables and .env loading
│   └── logger.py           # Structured logging configuration
├── agents/
│   ├── __init__.py
│   └── agent.py            # Agent factory function (initialize_recipe_agent, ~150 lines)
├── prompts/
│   ├── __init__.py
│   └── prompts.py          # System instructions (SYSTEM_INSTRUCTIONS constant, ~800 lines)
├── hooks/
│   ├── __init__.py
│   └── hooks.py            # Pre-hooks factory (get_pre_hooks, ~30 lines)
├── models/
│   ├── __init__.py
│   └── models.py           # Pydantic schemas (RecipeRequest, RecipeResponse, etc)
└── mcp_tools/
    ├── __init__.py         # Package marker
    ├── ingredients.py      # Image detection (pre-hook/tool modes)
    └── spoonacular.py      # SpoonacularMCP class (connection validation, retries)

tests/
├── unit/           # Schema validation, config loading, MCP init (fast, isolated)
│   ├── test_models.py
│   ├── test_config.py
│   ├── test_logger.py
│   ├── test_ingredients.py
│   ├── test_mcp.py
│   └── test_app.py
└── integration/    # E2E flows with real images and APIs
    ├── test_e2e.py
    └── test_api.py

images/             # Sample test images for verification

.docs/              # Documentation
├── PRD.md
├── DESIGN.md
└── IMPLEMENTATION_PLAN.md
```

**Module Organization - Responsibility Map:**
- **app.py** (50): Import factory → create AgentOS → serve (root level, single entry point)
- **src/agents/agent.py** (150): MCP init → DB config → Tools → Pre-hooks → Agent factory
- **src/prompts/prompts.py** (800): System instructions (pure data)
- **src/hooks/hooks.py** (30): Pre-hook factory (ingredient extraction + guardrails)
- **src/utils/config.py**: Environment variables, validation
- **src/utils/logger.py**: Structured logging (text/JSON)
- **src/models/models.py**: Pydantic schemas
- **src/mcp_tools/ingredients.py**: Image detection (core functions, async)
- **src/mcp_tools/spoonacular.py**: MCP initialization (async, retry logic)

## Implementation Guidelines

### Before Starting Any Task

1. **Query Context7 MCP** (CRITICAL):
   - Always query Context7 for latest library documentation before implementing
   - Check for current API patterns, best practices, deprecations
   - Verify Python version compatibility and breaking changes
   - Example: Query Context7 for Agno Agent before configuring; query for Pydantic before defining schemas

2. **Read Task Requirements**:
   - .docs/IMPLEMENTATION_PLAN.md has complete task specifications
   - Review input/output requirements, success criteria, constraints
   - Understand task dependencies before starting

3. **Reference Context**:
   - .docs/PRD.md for functional requirements and constraints
   - .docs/DESIGN.md for architectural decisions and data flows
   - This file for code quality and operational expectations

### After Completing Each Task

1. **Implement Tests** (REQUIRED):
   - Add unit tests for all new code (isolated, mocked externals)
   - Add integration tests for end-to-end flows (real APIs)
   - Use pytest as framework

2. **Run Full Test Suite**:
   - Execute `make test` (unit tests only, fast)
   - Execute `make eval` (integration tests, requires API keys)
   - Verify all tests pass before marking task complete

3. **Update Status** (REQUIRED):
   - Update Status Section in this file with:
     - Task [N] complete (date: YYYY-MM-DD)
     - Test results (all passing)
     - Any changes to README.md (if architectural details changed)
   - Never create separate tracking documents (IMPLEMENTATION_PLAN.md is the source of truth)

4. **Update README.md** (Only if needed):
   - README.md is the FINAL state documentation (not a rolling status)
   - Update only if architectural details, APIs, or setup changed
   - Audience: developers and code challenge reviewers
   - No other documentation files should be created

5. **Commit and Push to GitHub** (REQUIRED):
   - Stage all changes: `git add -A`
   - Commit with descriptive message: `git commit -m "Task [N]: Brief description of changes"`
   - Push to main: `git push origin main`
   - Verify changes appear on GitHub before proceeding to next task

### Code Quality Standards

**Python Best Practices:**
- Type hints on all functions and class methods
- Async operations for I/O (async/await pattern)
- Docstrings on all public functions and classes (concise, not verbose)
- Single responsibility functions (one clear purpose)
- Clear variable names (self-documenting code)

**Logging Implementation:**
- All files must use the logger: `from logger import logger`
- Structured logging (Python logging module)
- Log levels: DEBUG (dev info), INFO (important events), WARNING (unusual), ERROR (failures)
- Never log sensitive data (API keys, full images, passwords)
- Log request/response metadata for debugging (not raw data)

**Comments:**
- Essential comments only (why, not what)
- Code should be clear enough without comments
- Comments for non-obvious algorithms or business logic
- No commented-out code (use git history instead)

**Production Readiness:**
- Error handling for all external API calls (retry logic, graceful degradation)
- Input validation before processing (Pydantic schemas)
- Graceful error responses (no stack traces in API responses)
- Resource cleanup (close files, close connections properly)
- No hardcoded values (use environment variables)

## Do's & Don'ts

**DO**:
- Use system instructions to define agent behavior (not code)
- Leverage Agno built-in features (memory, retries, guardrails)
- Validate inputs/outputs with Pydantic schemas
- Store ingredient text in history (not base64 images)
- Initialize MCP with SpoonacularMCP class before agent creation
- Fail startup if external MCP unreachable (fail-fast pattern)
- Filter pre-hook ingredients by confidence threshold
- Ground responses in tool outputs (no hallucinations)
- Test incrementally (unit → integration after each task)
- Query Context7 MCP before implementing each task
- **Use async/await for ALL I/O operations**:
  - Network calls: `aiohttp.ClientSession` for URL fetches
  - Delays: `asyncio.sleep()` for all retry/backoff delays
  - All functions with I/O: Mark as `async def`, use `await`
  - Sync APIs: Wrap with `asyncio.to_thread()` (e.g., Gemini client, MCPTools)
  - Example: `result = await asyncio.to_thread(sync_func, arg1, arg2)`
- Implement comprehensive logging with structured format
- Run `make test` and `make eval` before marking task complete
- Update Status section after each task completion
- Update README.md only when architectural changes occur

**DON'T**:
- Write custom orchestration logic (Agno handles it)
- Create custom API routes (AgentOS provides them)
- Implement manual memory management (Agno automatic)
- Hardcode secrets (use environment variables)
- Store raw image bytes in memory or history
- Skip pre-hook execution for image requests
- Call recipe tools without ingredients
- Initialize MCP inline in app.py (use SpoonacularMCP class)
- Continue if MCP initialization fails (must fail startup)
- Log sensitive image data or API keys
- Create tracking or status documentation files
- Update README.md after every task (only on architectural changes)
- Add verbose comments or explanation comments (code should be self-documenting)
- Skip tests or mark tasks complete without running full test suite
- **Use synchronous I/O anywhere**:
  - ❌ `time.sleep()` - use `asyncio.sleep()` instead
  - ❌ `urllib.request` - use `aiohttp` instead
  - ❌ `requests` library - use `aiohttp` instead
  - ❌ Sync blocking calls in async functions - use `asyncio.to_thread()` wrapper
- Call `sync_function()` instead of `await asyncio.to_thread(sync_function)`
- Use blocking third-party libraries without wrapping in `asyncio.to_thread()`

## Configuration

Environment variables (load order: system env > .env > defaults):
- `GEMINI_API_KEY` (required) - Google Gemini vision API
- `SPOONACULAR_API_KEY` (required) - Recipe search API
- `GEMINI_MODEL` (default: gemini-1.5-flash)
- `PORT` (default: 7777)
- `MAX_HISTORY` (default: 3) - Conversation turns to keep
- `MAX_IMAGE_SIZE_MB` (default: 5) - Image upload limit
- `MIN_INGREDIENT_CONFIDENCE` (default: 0.7) - Vision API confidence filter
- `DATABASE_URL` (optional) - PostgreSQL for production

## Testing Strategy

**Required After Each Task:**
- Add unit tests for all new code (isolated, mocked externals)
- Add integration tests for end-to-end flows (where applicable)
- Run full test suite before marking task complete
- All tests must pass before proceeding to next task

**Unit Tests** (.docs/IMPLEMENTATION_PLAN.md Task 4-5):
- Schema validation
- Config loading
- Fast, isolated (no external calls)
- Run: `make test`

**Integration Tests** (.docs/IMPLEMENTATION_PLAN.md Task 10-11):
- E2E flows with real images
- Real API calls (requires valid keys)
- Session management
- Run: `make eval`

**Test Command Workflow:**
```bash
# After implementing a task:
make test   # Run unit tests (fast, no external APIs)
make eval   # Run integration tests (requires API keys)
# Both must pass before marking task complete
```

## Documentation Policy

**CRITICAL: Single README.md Only**
- ✅ README.md in root folder (comprehensive, final-state documentation)
- ❌ NO tracking documents (no CHANGES.md, SUMMARY.md, COMPLETION_LOG.md, etc.)
- ❌ NO rolling status files (README is final-state, not updated after each task)
- ❌ NO implementation notes or TODO lists in documentation

**README.md Content** (for developers and reviewers):
- Project overview and value proposition
- Quick start (make setup && make dev)
- Architecture overview and data flow
- Configuration reference (environment variables)
- API endpoint documentation
- Testing instructions (make test && make eval)
- Troubleshooting common issues
- References to detailed docs (.docs/PRD.md, .docs/DESIGN.md, .docs/IMPLEMENTATION_PLAN.md)

**When to Update README.md:**
- After implementing major architectural changes
- After changing setup or deployment procedures
- After modifying API endpoints or response formats
- After changing configuration requirements
- Only update, never create separate documentation files

## External MCP Server

**Spoonacular Recipe MCP**:
- External Node.js service (runs via npx)
- Provides: search_recipes(), get_recipe_information_bulk()
- Startup validation required (application fails if unreachable)
- Requires: SPOONACULAR_API_KEY environment variable
- No custom validation code needed (AgentOS handles it)

## Makefile Usage

All development and deployment tasks use the Makefile:

```bash
make setup       # Install deps, create .env from .env.example
make dev         # Start: python app.py (development mode)
make run         # Production: python app.py
make test        # Unit tests: pytest tests/unit/ -v
make eval        # Integration tests: pytest tests/integration/ -v
make clean       # Remove cache files (__pycache__, *.pyc)
```

**Important:** Use `make` commands exclusively. Do not run `python app.py` directly for development; use `make dev`.

## Key References

- **Functional requirements**: .docs/PRD.md
- **Technical design & architecture**: .docs/DESIGN.md
- **Task specifications**: .docs/IMPLEMENTATION_PLAN.md
- **Project documentation**: README.md (root folder, final-state)
- **Development guidelines**: This file (copilot-instructions.md)
