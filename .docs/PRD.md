# Product Requirements Document (PRD)

## Project Title
**Image-Based Recipe Recommendation Service**

---

## Purpose & Vision

This project demonstrates **production-quality GenAI system design** using modern orchestration patterns (AgentOS, Agno Agent, MCP).

**Core Goal:** Transform ingredient images into structured recipe recommendations with full conversational memory and preference tracking.

**Key Design Principle:** Keep the system **simple, explicit, and reviewable** by leveraging AgentOS as the complete runtime backbone. This means no custom orchestration code, no manual memory management, and no infrastructure boilerplate—just configuration and business logic.

---

## In-Scope Functionality

### Core Capabilities
1. Accept ingredient input via:
   - Image (URL or base64 bytes)
   - Text (explicit ingredient list)
2. Detect ingredients from images using vision AI
3. Generate recipe recommendations based on detected ingredients
4. Incorporate user preferences and nuances (dietary restrictions, cuisines, meal types)
5. Maintain conversational context across multiple turns
6. Enforce domain boundaries (recipes only)
7. Provide structured, validated outputs
8. Expose functionality via REST API and Web UI

### What Gets Built
- **Single AgentOS Application** serving both REST API and Web UI simultaneously
- **Session-based memory** for persistent conversation context
- **Ingredient detection** from images (vision-based)
- **Recipe search** integration with external recipe service
- **Automatic preference tracking** (diet, allergies, cuisines, etc.)
- **Built-in observability** (tracing, evaluations)

---

## Out of Scope

- User authentication / authorization
- Custom UI frameworks (built-in AGUI is provided)
- Image preprocessing or segmentation
- Nutritional analysis or shopping lists
- Internationalization
- Rate limiting / throttling

---

## High-Level System Overview

### Architecture: Single Orchestrator + Focused Tools

The system uses **Agno Agent** as a stateful orchestrator that manages conversation memory and tool calling. AgentOS wraps everything to provide REST API, Web UI, and infrastructure automatically.

```
┌─────────────────────────────────────────────────────────────┐
│  AgentOS (Complete Runtime)                                  │
│  • Serves REST API at /api/agents/chat                       │
│  • Serves Web UI (AGUI) at http://localhost:7777             │
│  • Manages tool lifecycle and connections                    │
│  • Built-in tracing and evaluations                          │
└─────────────────────────────────────────────────────────────┘
              ↓                                     ↓
    ┌──────────────────────────────┐    ┌─────────────────────────┐
    │ Agno Agent (Orchestrator)    │    │ Spoonacular Recipe MCP  │
    │ • Chat history per session   │    │ (External Service)      │
    │ • Preference tracking        │    │ • Search recipes        │
    │ • Tool routing logic         │    │ • Return structured data│
    │ • Response synthesis         │    └─────────────────────────┘
    └──────────────────────────────┘
         ↓
    ┌──────────────────────────────┐
    │ Ingredient Detection         │
    │ (Pre-hook Pattern)           │
    │ • Extract from image         │
    │ • Filter by confidence       │
    │ • Append to message          │
    └──────────────────────────────┘
```

**Key Design: Pre-Hook Pattern**
- Images processed **before** agent executes
- Eliminated extra LLM round-trip
- Agent focuses on recipe selection
- Ingredients stored as text in history (not bytes)

---

## Functional Requirements

### FR-1: Input Handling & Interfaces

The system exposes **two built-in interfaces** (provided by AgentOS):

**REST API Interface**
- JSON endpoints for programmatic access
- Input validation via Pydantic schemas
- Ideal for integrations and automated workflows
- Automatically generated OpenAPI documentation

**Web UI Interface (AGUI)**
- ChatGPT-like interactive interface
- View conversation history and memories
- Upload images, send messages, see responses in real-time
- Ideal for manual testing and exploration

Both interfaces serve the same agent and share session memory.

**Image Input Options:**
- `image_url`: URL to ingredient image (HTTP/HTTPS)
- `image_base64`: Base64-encoded image bytes

**Validation Rules:**
- Supported formats: JPEG, PNG
- Maximum size: 5MB (configurable)
- At least one of: image, text ingredients, or conversation history must be available
- Request validation returns appropriate HTTP error codes (400, 413, 422)

---

### FR-2: Session-Based Conversation Memory

The system uses **Agno Agent's built-in session memory** to maintain conversational context automatically.

**Core Memory Features:**
- **Chat History**: Automatically includes last N conversation turns (configurable, default 3)
- **User Preferences**: Dietary restrictions, allergies, cuisines, meal types—captured and persisted
- **Session Identification**: Each conversation has a unique `session_id` 
- **Persistence**: Data stored in SQLite (development) or PostgreSQL (production)
- **Context Compression**: Automatic summarization when conversations get long
- **FIFO Eviction**: Oldest entries dropped when memory limit reached

**How It Works:**
- Client provides or receives `session_id`
- Agno automatically loads conversation history for that session
- User preferences are extracted from messages and persisted
- Follow-up queries automatically reference stored preferences
- Session data persists across restarts

**Benefits:**
- No manual session management code required
- Preferences remembered without explicit extraction logic
- Conversational flow feels natural (agent refers back to stated preferences)
- Chat history available for context and transparency

**Configuration:**
- `MAX_HISTORY`: Maximum conversation turns to keep (default: 3)
- `ENABLE_SESSION_SUMMARIES`: Auto-generate summaries for long conversations
- `COMPRESS_TOOL_RESULTS`: Enable automatic context compression
- `DATABASE_URL`: Optional PostgreSQL connection (uses SQLite if not provided)

---

### FR-3: Ingredient Detection Pattern

The system uses a **pre-hook pattern** for ingredient extraction—this runs **before** the agent executes.

**How It Works:**
1. Request arrives with image
2. Pre-hook extracts ingredients using Gemini vision API
3. Pre-hook appends extracted ingredients to user message as clean text
4. Agent receives enriched message: "Show me recipes\n\n[Detected Ingredients] tomato, basil"
5. Agent never processes raw images, only clean ingredient text

**Why This Pattern?**
- ✅ **Eliminates extra LLM call**: Gemini called once (pre-hook), not again by agent
- ✅ **Faster responses**: No extra round-trip
- ✅ **Cleaner orchestration**: Agent focused on recipes, not image analysis
- ✅ **Better memory**: Chat history includes ingredients as text (not image bytes)
- ✅ **Simpler system instructions**: No image-handling logic needed

**Alternative: Agent-Called Tool**
For scenarios requiring agent-side visibility and refinement, ingredient detection could be moved to a tool decorator. This would:
- Give agent visibility into image analysis quality
- Allow agent to ask for clarification or refinement
- Trade-off: One extra LLM call + more complex system instructions

**Configuration:**
- `MIN_INGREDIENT_CONFIDENCE`: Minimum confidence threshold (default: 0.7)
- `MAX_IMAGE_SIZE_MB`: Maximum image size (default: 5)

**Behavior:**
- Only runs if images present in request
- Validates format (JPEG/PNG) and size before processing
- Calls Gemini vision API once per image
- Filters results by confidence threshold
- Appends clean ingredient list to message
- Clears image bytes from input (prevents re-processing)

---

### FR-4: Preference Tracking

The system automatically tracks and applies user preferences through **Agno's agentic memory**.

**What Gets Tracked:**
- Diet preferences: vegetarian, vegan, gluten-free, dairy-free, paleo, keto, etc.
- Allergies/intolerances: shellfish, peanuts, tree nuts, dairy, eggs, fish, wheat, etc.
- Cuisine preferences: italian, asian, mexican, indian, mediterranean, etc.
- Meal types: breakfast, lunch, dinner, dessert, appetizer, etc.
- Cooking time preferences: quick meals, slow cooking, etc.

**How It Works:**
- Preferences extracted from user messages by Agno Agent
- Stored automatically in agent memory per session
- Persisted across conversation turns (even after restart if same `session_id`)
- Applied to subsequent tool calls without explicit routing
- Reference naturally in responses ("As you mentioned before, you prefer vegetarian...")

**Example Flow:**
- Turn 1: "What Italian vegetarian recipes?" → Agent extracts: diet=vegetarian, cuisine=italian
- Turn 2: "Any dessert ideas?" → Agent remembers previous preferences, applies them by default
- Turn 3: "Actually, I'm vegan now" → Agent updates preferences, applies new setting going forward

---

### FR-5: Recipe Generation

The system integrates an **external recipe service via MCP** for generating recipe recommendations.

**Service: Spoonacular Recipe MCP**
- External Node.js service (runs via npx without repo checkout)
- Provides recipe search via MCP protocol
- Requires `SPOONACULAR_API_KEY` environment variable
- Stateless (no memory between calls)
- Startup validation: **Required** (application fails if unable to connect)

**Recipe Search Parameters:**
- Ingredients (required): Detected or provided ingredients
- Diet (optional): Dietary restrictions to filter recipes
- Intolerances (optional): Allergies or intolerances to exclude
- Cuisine (optional): Preferred cuisine type
- Meal type (optional): Type of meal (main course, dessert, etc.)
- Number of results (optional): How many recipes to return

**How Agno Uses It:**
- Agent automatically passes extracted ingredients and preferences as parameters
- No manual routing or wrapper code needed
- Recipe results used to synthesize response to user
- All information grounded in Spoonacular data (no hallucination)

**Why This Approach:**
- ✅ Always up-to-date recipes (Spoonacular maintains database)
- ✅ 50K+ verified recipes
- ✅ Simple integration (single MCP call)
- ✅ Zero data pipeline overhead (no ETL, vectorization, or maintenance)
- ⚠️ Tradeoff: Requires internet connection and API key

---

### FR-6: Agent Decision Logic

The **Agno Agent** is the central intelligence. Its behavior is defined through **system instructions**, not code.

**Core Responsibilities:**

1. **Domain Enforcement**: Only answer recipe-related questions; politely refuse off-topic requests
2. **Ingredient Prioritization**: 
   - Use pre-detected ingredients from image (if available)
   - Fall back to ingredients mentioned in message
   - Reference ingredients from conversation history
   - Ask for clarification if no ingredients available
3. **Preference Extraction**: Automatically infer diet, allergies, cuisines, meal types from natural language
4. **Tool Routing**: Decide when to call recipe tool based on context
5. **Response Synthesis**: Ground responses in tool outputs and conversation history (no hallucination)

**System Instructions Guide:**
The agent receives detailed written instructions covering:
- Domain boundaries (what questions are in-scope vs. out-of-scope)
- How to extract preferences from natural language
- Ingredient source prioritization
- When to call tools vs. respond conversationally
- How to handle edge cases (preference changes, follow-ups, clarifications)

**Agent Automatically Handles:**
- Loading session history
- Applying guardrails (via pre-hooks)
- Deciding which tools to call
- Extracting and storing preferences
- Synthesizing responses grounded in tool outputs
- Storing conversation turns

---

### FR-7: Guardrails & Domain Boundaries

The system enforces domain boundaries to keep responses focused and safe.

**Recipe-Related (✅ In-Scope):**
- Generating recipes from ingredients
- Ingredient substitutions
- Dietary accommodations
- Cuisine and meal type recommendations
- Cooking methods and techniques

**Not Recipe-Related (❌ Out-of-Scope):**
- Nutritional analysis or calorie counting
- Food history or trivia
- Personal dietary or medical advice
- General conversation unrelated to recipes

**How It's Enforced:**
- System instructions define domain boundaries clearly
- Off-topic requests refused with helpful message
- Tools not called for off-topic requests
- Optional pre-hook guardrails for additional safety (PII detection, prompt injection)

---

### FR-8: Structured Inputs & Outputs

All agent inputs and outputs are validated through **Pydantic schemas**.

**Input Validation:**
- Requests validated against `RecipeRequest` schema
- Required fields enforced
- Type checking (list, string, optional fields)
- Invalid requests rejected with clear error messages

**Output Validation:**
- Responses validated against `RecipeResponse` schema
- All recipes include required fields (title, ingredients, instructions, times)
- Consistent, predictable API contract
- Full mypy/Pylance type safety

**Benefits:**
- Early error detection (before processing)
- Clear API documentation (schemas auto-generate OpenAPI docs)
- Type-safe code
- Clean JSON serialization

---

### FR-9: Configuration Management

All configuration is centralized and environment-based.

**Configuration Sources (Priority):**
1. System environment variables (highest priority)
2. `.env` file values
3. Hardcoded defaults (lowest priority)

**Required Variables:**
- `GEMINI_API_KEY`: API key for vision model (ingredient detection)
- `SPOONACULAR_API_KEY`: API key for recipe search

**Optional Variables (with defaults):**
- `GEMINI_MODEL`: Model name (default: gemini-1.5-flash)
- `PORT`: Server port (default: 7777)
- `MAX_HISTORY`: Max conversation turns (default: 3)
- `MAX_IMAGE_SIZE_MB`: Max image size (default: 5)
- `MIN_INGREDIENT_CONFIDENCE`: Confidence threshold (default: 0.7)
- `DATABASE_URL`: PostgreSQL connection (uses SQLite if not set)

**Rules:**
- No secrets hardcoded in code
- `.env` file included in `.gitignore`
- `.env.example` in repo without sensitive values
- All settings accessible via environment variables

---

### FR-10: Observability & Tracing

**AgentOS provides built-in tracing** with no external SaaS dependencies.

**What Gets Traced:**
- Agent runs (start time, end time, duration)
- Tool calls (which tools, parameters, execution time)
- Model calls (tokens used, latency)
- Errors and exceptions with context
- Session metadata (preferences, ingredients)

**Evaluation Support:**
- Built-in evaluation framework for ingredient detection accuracy
- LLM-as-judge for recipe relevance scoring
- Results stored and queryable via AgentOS APIs

**Benefits:**
- Understand system behavior and decision-making
- Debug issues with full context
- Measure accuracy and performance
- No external services to configure

---

### FR-11: Testing Strategy

**Unit Tests**
- Schema validation
- Configuration loading
- Guardrail behavior
- Fast, isolated, no external calls

**Integration Tests (Agno Evals)**
- End-to-end flows with real images
- Ingredient detection accuracy verification
- Recipe recommendation quality
- Conversation flows with session memory
- Results stored in AgentOS eval database

**Test Execution:**
- Unit tests: `make test`
- Integration tests: `make eval`
- Coverage reporting available

---

### FR-12: Development Experience

**Single Entry Point:**
```
python app.py
```

This single command:
- Starts Agno Agent with automatic retries
- Initializes external MCPs
- Serves REST API at http://localhost:7777
- Serves Web UI at http://localhost:7777
- Enables hot-reload in dev mode

**Retry Configuration:**
- Automatic retries on model API failures
- Exponential backoff (1s → 2s → 4s)
- Configurable retry count and delay
- Handles transient failures gracefully

**Makefile Commands:**
- `make setup`: Install dependencies, configure environment
- `make dev`: Run with hot-reload (development)
- `make run`: Production run (no hot-reload)
- `make test`: Unit tests
- `make eval`: Integration tests
- `make clean`: Remove cache files

**Development Workflow:**
1. `make setup` - First-time setup
2. `make dev` - Start server
3. Use REST API via curl/Postman or AGUI at http://localhost:7777
4. Changes auto-reload in dev mode
5. Run tests anytime

---

### FR-13: Error Handling & Response Format

**Success Response (HTTP 200):**
```json
{
  "session_id": "unique conversation identifier",
  "run_id": "unique interaction identifier",
  "response": "natural language response",
  "ingredients": ["ingredient1", "ingredient2"],
  "recipes": [list of recipe objects],
  "metadata": {
    "tools_called": ["tool1", "tool2"],
    "model": "gemini-1.5-flash",
    "response_time_ms": 1234
  }
}
```

**Error Responses:**
- `400 Bad Request`: Malformed input, missing required fields, invalid format
- `413 Payload Too Large`: Image exceeds MAX_IMAGE_SIZE_MB
- `422 Unprocessable Entity`: Valid format but business logic failure (e.g., off-topic query)
- `500 Internal Server Error`: Unexpected system errors

**Error Response Format:**
- Includes error type, human-readable message
- Preserves session_id and run_id if available

---

## Non-Functional Requirements

### NFR-1: Code Quality
- Single-responsibility functions
- Clear, descriptive naming
- Modular structure
- Reusable components
- Well-documented

### NFR-2: Reliability
- Graceful handling of LLM failures
- Automatic retries with exponential backoff
- Deterministic output validation
- Sensible error messages

### NFR-3: Performance
- Designed for local execution
- Response times captured and reported
- No unnecessary LLM calls
- Reasonable latency (<10 seconds typical)

### NFR-4: Maintainability
- Clear separation of concerns
- Easy to understand from documentation
- Minimal coupling between components
- Easy to extend with new tools or change instructions

### NFR-5: Security
- No secrets in code
- No logging of raw image bytes (privacy)
- Input validation and guardrails

---

## Architecture Decisions

### Why AgentOS as Complete Runtime

**AgentOS provides the entire application backbone:**
- REST API (automatic, built-in)
- Web UI (automatic, built-in)
- Agent orchestration
- Session management
- MCP tool lifecycle management
- Tracing and observability

**Benefit:** Single `python app.py` command starts complete system. No custom FastAPI routes, no manual session management, no infrastructure boilerplate.

**Tradeoff:** Less flexibility than custom implementation, but dramatically simpler and faster to build.

---

### Why Pre-Hook Pattern for Ingredient Detection

**Pre-hook executes before agent starts:**
- Processes image immediately
- Extracts ingredients
- Appends clean text to message
- Agent receives: "What recipes?\n\n[Detected Ingredients] tomato, basil"

**Benefits:**
- ✅ One vision API call (not two LLM calls)
- ✅ Faster response times
- ✅ Cleaner agent orchestration
- ✅ Better memory (text, not image bytes)
- ✅ Natural separation (API handles images, agent handles recipes)

**Alternative Pattern:** Could be implemented as @tool decorator for maximum agent flexibility, but would add one LLM round-trip.

---

### Why Spoonacular MCP for Recipe Search

**External API via MCP instead of RAG pipeline:**

**Advantages:**
- ✅ 50K+ verified recipes (always up-to-date)
- ✅ Zero data pipeline overhead (no ETL, vectorization, preprocessing)
- ✅ Simple integration (single MCP call)
- ✅ Minimal infrastructure (just API key)
- ✅ No maintenance (Spoonacular maintains recipes)
- ✅ Fast time-to-value

**Tradeoff:**
- Requires internet connection
- Per-call costs (free tier limited)
- Limited customization vs. self-hosted

**Alternative:** RAG pipeline with semantic search
- Would require: Recipe collection, ETL, vectorization, vector database, ongoing maintenance
- **Trade-off:** More control but 3-5x more infrastructure complexity
- **When to use:** Only if you need semantic nuance or proprietary recipes

**Decision:** MCP approach chosen for simplicity and time-to-value appropriate for code challenge.

---

### Why SQLite for Development (PostgreSQL Optional for Production)

**Code Challenge / Development (Default):**
- SQLite + LanceDB (file-based, zero setup)
- Perfect for: Rapid development, code reviews, running anywhere
- Benefits: Clone repo → `make setup && make dev` → works immediately

**Production (Optional Enhancement):**
- PostgreSQL + pgvector (optional, not required for code challenge)
- Configured via `DATABASE_URL` environment variable
- Benefits: ACID compliance, concurrent writes, standard practices
- Switch: Config only, no code changes

---

## Success Criteria

A reviewer should be able to:

**Functional Success**
- Run `make setup && make dev` and access both interfaces immediately
- Send image via REST API (curl/Postman) and receive structured recipes
- Verify ingredients detected correctly from images (>80% accuracy on clear images)
- Test multi-turn conversations with same `session_id`
- Confirm preferences persist across turns
- Verify guardrails prevent off-topic requests

**Technical Success**
- All unit tests pass (`make test`)
- All integration tests pass (`make eval`)
- Traces visible with proper metadata
- Response times reasonable (<10 seconds typical)
- Code well-structured and documented
- Single command startup: `python app.py`

**Code Quality**
- Clear separation of concerns
- No custom orchestration code (system instructions instead)
- No custom memory management (Agno handles it)
- No custom API routes (AgentOS provides them)
- Minimal glue code (~150-200 lines)
- Easy to understand and extend

**Extensibility**
- Understand architecture from documentation
- Easily identify where to add new tools
- Clear how to modify agent behavior (system instructions)
- Know how to add new preferences or domains
