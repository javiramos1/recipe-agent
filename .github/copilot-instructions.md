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
9. **Async/await for I/O**: All I/O operations (API calls, file I/O, database) must be async
10. **Never log sensitive data**: No API keys, passwords, images, or PII in logs
11. **Commit and push after each task**: `git add -A`, `git commit -m "Task [N]: description"`, `git push origin main`
12. **Follow Do's & Don'ts strictly** (see below)
13. **Always update this file status section** after completing each task
14. **Always use makefile commands** for setup, dev, test, eval, run, clean. Do not use python app.py directly.

**Critical Architecture Patterns:**
11. **Pre-hook pattern**: Images processed BEFORE agent executes. Extract ingredients → append as text → clear images from input. Agent only sees ingredient text.
12. **Two-step recipe process**: NEVER generate recipe instructions without calling `get_recipe_information_bulk`. Always: search_recipes → get_recipe_information_bulk (prevents hallucinations).
13. **Never store images**: Base64/image bytes NEVER in memory or database. Only ingredient TEXT in chat history.
14. **System instructions define behavior, NOT code**: Orchestration logic goes in Agno system instructions, not Python code. Let Agno handle tool routing, memory, retries.
15. **Single entry point**: Everything runs from `python app.py`. No separate servers or multiple terminals.
16. **No custom code for**: Orchestration logic, API routes, memory management, session storage. AgentOS/Agno provide these automatically.
17. **MCP validation at startup only**: Only external MCPTools (Spoonacular) need startup validation. Local @tool functions don't need validation.
18. **Agno handles automatically**: Memory, retries with exponential backoff, guardrails, context compression, preference extraction. Don't implement these manually but do use Agno AI features.

## Project Overview

This is a code challenge implementing a production-quality GenAI system that transforms ingredient images into recipe recommendations using modern orchestration patterns (AgentOS, Agno Agent, MCP). The service demonstrates best practices in system design, testing, and implementation.

**Core Value Proposition:** Single-command startup (`python app.py`) providing REST API + Web UI + stateful conversational agent with automatic memory, retries, and guardrails.

## Status Section

**Current Status: Phase 1 complete (Tasks 1-5 + 2.5), Task 6 complete, all unit tests passing (95 tests), ready for Phase 2 (Tasks 7-9)**

### Phase 1: Foundational (Tasks 1-5 + Task 2.5 logger)
- [x] Task 1 complete (date: 2026-01-18) - Project structure, dependencies, .gitignore
- [x] Task 2 complete (date: 2026-01-18) - Configuration Management (config.py) with environment variable loading and validation
- [x] Task 2.5 complete (date: 2026-01-18) - Logging Infrastructure (logger.py) with JSON and Rich text formatting, 20 passing tests
- [x] Task 3 complete (date: 2026-01-18) - Data Models (models.py) with 5 Pydantic schemas (RecipeRequest, Ingredient, Recipe, RecipeResponse, IngredientDetectionOutput)
- [x] Task 4 complete (date: 2026-01-18) - Unit Tests - Models (test_models.py) with 38 passing tests, all validations working
- [x] Task 5 complete (date: 2026-01-18) - Unit Tests - Configuration (test_config.py) with 11 passing tests, env var precedence verified

### Phase 2: Core Features (Tasks 6-9)
- [x] Task 6 complete (date: 2026-01-18) - Ingredient Detection Pre-Hook (ingredients.py) with Gemini vision API integration, 25 unit tests passing, using filetype package for image validation, google-genai package for latest API

### Phase 3: Testing & Docs (Tasks 10-15)
- [ ] Task 10: Integration Tests E2E - Pending
- [ ] Task 11: REST API Testing - Pending
- [x] Task 12 complete (date: 2026-01-18) - Makefile with all development commands
- [ ] Task 13: Sample Test Images - Pending
- [x] Task 14 complete (date: 2026-01-18) - Comprehensive README.md
- [ ] Task 15: Final Validation - Pending

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

Single-entry-point application (`python app.py`):
- **AgentOS** (runtime): REST API, Web UI, MCP lifecycle management, built-in tracing
- **Agno Agent** (orchestrator): Stateful memory, automatic retries, tool routing, guardrails
- **Pre-hook** (ingredients.py): Vision API integration → ingredient extraction → request enrichment
- **Spoonacular MCP** (external): Recipe search with filtering (dietary, cuisine, type)

**Data Flow:**
Request → Pre-hook (image processing) → Agent (orchestration) → MCP (recipe search) → Response

## Key Principles

**Architecture & Design:**
- Single entry point (app.py ~150-200 lines, no custom FastAPI or orchestration code)
- No custom orchestration logic (use Agno Agent with system instructions instead)
- No custom memory management (Agno automatic session persistence)
- No custom API routes (AgentOS provides REST/Web UI automatically)
- Pre-hook pattern eliminates LLM round-trip (image → ingredients → message in one call)
- Images never stored in memory (only ingredient text in chat history)
- MCP startup validation (fail startup if external tools unreachable)
- Structured validation everywhere (Pydantic schemas for all inputs/outputs)

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


## Module Structure

```
app.py              # AgentOS application (agent config, pre-hooks, orchestration)
config.py           # Environment variables and .env loading
models.py           # Pydantic schemas (RecipeRequest, RecipeResponse, etc)
ingredients.py      # Pre-hook function for image → ingredient extraction

tests/
├── unit/           # Schema validation, config loading (fast, isolated)
└── integration/    # E2E flows with real images and APIs

images/             # Sample test images for verification
```

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
- Fail startup if external MCP unreachable
- Filter pre-hook ingredients by confidence threshold
- Ground responses in tool outputs (no hallucinations)
- Test incrementally (unit → integration after each task)
- Query Context7 MCP before implementing each task
- Use async/await for all I/O operations
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
- Log sensitive image data or API keys
- Create tracking or status documentation files
- Update README.md after every task (only on architectural changes)
- Add verbose comments or explanation comments (code should be self-documenting)
- Skip tests or mark tasks complete without running full test suite

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
