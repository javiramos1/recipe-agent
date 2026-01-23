# Solution Design Document  
**Image-Based Recipe Recommendation Service (AgentOS/Agno-based)**

---

## 1. Purpose of This Document

**Learning & Reference Implementation**

This document provides a **comprehensive design reference for agentic applications**. The recipe recommendation service is intentionally used as a learning vehicle—a simple problem domain enhanced with **production-grade patterns, capabilities, and architectural decisions** to demonstrate professional practices in GenAI system design.

**What This Design Teaches:**
- Complete development lifecycle: Requirements → Design → Implementation → Testing → Monitoring
- Modern agentic framework patterns using AgentOS and Agno Agent
- Advanced memory management, knowledge bases, and preference tracking
- Tool design and external service integration via MCP protocol
- Structured outputs, validation, and type safety
- Hook systems for pre/post processing and guardrails
- Observability, tracing, and evaluation frameworks
- Testing strategies from unit to integration to evaluation

**Intentional Complexity for Learning:**
This solution demonstrates that even simple problems become rich case studies when applying professional engineering practices. The application is *deliberately over-engineered* to showcase each architectural pattern in a real, working system.

Its primary goals are to:
- Document **production-grade architecture and design decisions**
- Explain **intent, constraints, and trade-offs** for each pattern
- Provide a **reference for agentic application design**
- Enable **code review and architectural understanding**
- Serve as **learning material for framework best practices**

This document goes beyond "what" and explains **"why" and "how"** each decision was made, while avoiding full code listings (see IMPLEMENTATION_PLAN.md for detailed task specifications).

---

## 2. Design Goals & Non-Goals

### 2.1 Design Goals

- Build a **production-ready reference implementation** using AgentOS
- Demonstrate **tool-based orchestration** (internal @tool + external MCP)
- Showcase **structured outputs everywhere** (Pydantic validation)
- Leverage **built-in Agno features** (memory, retries, guardrails, compression)
- Keep the system **simple, explicit, and maintainable**
- Optimize for **clarity and long-term extensibility**
- Support both **local development** (SQLite/LanceDB) and **enterprise deployment** (PostgreSQL + pgvector)
- **Intentionally demonstrate comprehensive agentic patterns** even though the problem domain is simple

### 2.1a Intentional Over-Engineering for Learning

This solution is **deliberately over-engineered** to be an effective learning vehicle:

**The Problem Domain is Simple**
A recipe recommendation system could be built in:
- ✅ 50 lines: Basic API call → parse JSON → return results
- ✅ 200 lines: Add image processing + caching

**Why 2000+ Lines with Comprehensive Patterns?**

This project demonstrates that **professional engineering practices create value** even for simple problems:

1. **Memory Management**: Users get personalized experience across conversations
2. **Knowledge Base**: System learns from past failures, improves over time
3. **Structured Outputs**: Type-safe responses prevent integration bugs
4. **Observability**: Production support teams debug issues with full context
5. **Testing**: Confidence in behavior across refactoring and scaling
6. **State Management**: Handle multi-user deployments with consistency
7. **Tool Orchestration**: Pattern applicable to complex multi-step workflows
8. **Guardrails**: Prevent hallucinations and domain violations

**What Gets Taught Through Over-Engineering**

| Pattern | Simple Version | Production Version | Learning Value |
|---------|---|---|---|
| **Input Handling** | String → string | Pydantic v2 with Field constraints | Type safety, validation, OpenAPI |
| **Memory** | None | Session-based with persistence | User experience, state management |
| **Preferences** | Hardcoded | Agentic extraction + persistence | Preference learning, personalization |
| **Tools** | Function calls | MCP + @tool decorator | Integration patterns, modularity |
| **Testing** | Manual | 140+ unit + integration + evaluation tests | Quality assurance processes |
| **Logging** | print() | Structured JSON/text with levels | Production debugging |
| **Tracing** | None | OpenTelemetry with AgentOS | Performance analysis |
| **Error Handling** | try/except | Retries, guardrails, graceful degradation | Reliability patterns |
| **Knowledge** | None | LanceDB semantic search | Learning systems |

**The Payoff**: Someone studying this codebase learns not just "how to build recipe apps" but **how to architect production agentic systems**.

---

### 2.2 Non-Goals

- Maximum performance or scale
- Custom UI frameworks (using built-in AGUI)
- Complex data pipelines (using Spoonacular API)
- Custom orchestration logic (Agno handles this)

---

## 3. Key Design Decisions (Rationale)

This section explains the most important architectural choices.

### 3.1 Why AgentOS as the Complete Runtime

AgentOS provides the **complete application backbone** in a single entry point:

**What AgentOS Provides:**
- Built-in REST API (FastAPI endpoints automatically generated)
- Built-in Web UI (AGUI at http://localhost:7777)
- Agent orchestration with automatic tool calling
- Session management and memory persistence
- Built-in tracing and evaluations (no external SaaS)
- MCP lifecycle management

**Trade-off:**  
Less flexibility than building custom FastAPI, but dramatically simpler and faster. Eliminates ~950 lines of boilerplate code.

**Why This Matters:**  
- Single command to run entire system: `python app.py`
- Both REST API and Web UI served simultaneously
- No custom routing, memory management, or API layer code
- Focus on business logic, not infrastructure

---

### 3.2 Why Agno Agent for Orchestration

Agno Agent is the **central intelligence** with built-in capabilities:

**Core Features Used:**
- **Session-based memory**: Automatic chat history per `session_id`
- **User preferences memory**: Extracted and persisted automatically
- **Automatic retries**: Exponential backoff on failures (configurable)
- **Structured I/O**: Pydantic validation for inputs and outputs
- **Guardrails**: Built-in PII detection and prompt injection protection
- **Context compression**: Automatic summarization after N tool calls
- **Tool routing**: Decides which tools to call based on system instructions

**Trade-off:**  
Declarative system instructions instead of imperative orchestration code. Less fine-grained control, but significantly more maintainable.

**Why This Matters:**  
- No manual memory management (Agno handles session storage)
- No custom retry logic (built-in with exponential backoff)
- No manual preference tracking (agentic memory inference)
- System instructions define behavior, not code

---

### 3.2b Async/Await Design for Non-Blocking I/O

**CRITICAL Design Requirement:** All I/O operations must be asynchronous to prevent blocking the event loop. This enables concurrent request handling and proper resource utilization in production.

**Async I/O Architecture:**

- **Network HTTP calls** → Use `aiohttp.ClientSession` (async HTTP client)
  - Image fetches from URLs: `async with session.get(url) as resp: await resp.read()`
  - Replace: `urllib.request.urlopen()` (synchronous, blocks event loop)

- **Vision API calls** → Wrap sync Gemini client with `asyncio.to_thread()`
  - Prevents blocking event loop during API calls
  - Pattern: `result = await asyncio.to_thread(client.models.generate_content, ...)`
  - Allows other requests to be processed concurrently

- **Retry delays** → Use `asyncio.sleep()` (non-blocking waits)
  - Exponential backoff: `await asyncio.sleep(2 ** attempt)`
  - Replace: `time.sleep()` (synchronous, blocks all concurrent requests)

- **Function signatures:**
  - All functions doing I/O: `async def function_name(...)`
  - All I/O operations in async functions: `await operation()`
  - Retry logic: Async wrappers around sync operations

**Implementation Points:**

1. **ingredients.py** - Core image processing (async):
   - `async def fetch_image_bytes(url)` → `aiohttp` instead of `urllib`
   - `async def extract_ingredients_from_image(bytes)` → `asyncio.to_thread(gemini_api_call)`
   - `async def extract_ingredients_with_retries(bytes)` → `asyncio.sleep()` for retry backoff
   - `async def extract_ingredients_pre_hook(...)` → awaits all I/O functions
   - `async def detect_ingredients_tool(...)` → awaits all I/O functions

2. **mcp_tools/spoonacular.py** - MCP initialization (async):
   - `async def initialize()` → MCP connection with retry logic
   - Retry delays: `await asyncio.sleep(delay)` instead of `time.sleep()`
   - Wrap sync MCPTools creation: `await asyncio.to_thread(MCPTools, ...)`

3. **agent.py** - Agent factory (async):
   - `async def initialize_recipe_agent()` → calls async MCP init
   - All I/O in initialization: `mcp_tools = await spoonacular_mcp.initialize()`

4. **app.py** - Application startup (uses asyncio.run):
   - At module level: `agent = asyncio.run(initialize_recipe_agent())`
   - Creates event loop for async startup sequence
   - AgentOS serves synchronously thereafter

**Why This Matters:**
- ✅ **Concurrent request handling**: Multiple requests can be processed without blocking each other
- ✅ **Resource efficiency**: Thread pool not saturated with blocked operations
- ✅ **Production-ready**: Essential for scalability and responsiveness
- ✅ **Modern Python patterns**: Aligns with fastapi/asyncio best practices
- ⚠️ **Non-negotiable**: All code violating async patterns must be refactored

---

### 3.3 Ingredient Detection: Tool-Based Pattern

The ingredient detection is implemented as an **internal Agno @tool** that the agent can call during orchestration.

**Architecture: Core Functions in ingredients.py**
- Reusable helper functions for image processing:
  - `fetch_image_bytes(image_data)`: Get image bytes from URL or base64
  - `validate_image_format()`: Check for JPEG/PNG format
  - `validate_image_size()`: Enforce MAX_IMAGE_SIZE_MB limit
  - `extract_ingredients_from_image()`: Call Gemini vision API with retries
  - `parse_gemini_response()`: Extract structured ingredient data
  - `filter_ingredients_by_confidence()`: Apply confidence threshold

**Tool Pattern** (Current Implementation)
- Registered as `@tool` decorator: `detect_image_ingredients(image_data: str)`
- Returns `IngredientDetectionOutput` with ingredients and confidence scores
- Agent decides when to call based on user message and system instructions
- Integrated with agent memory and conversation history
- **Benefits:** Agent has visibility, can ask clarifying questions, full orchestration control

**Why Tool Pattern:**
- ✅ **Agent visibility**: Tool calls appear in execution trace
- ✅ **Smart activation**: Agent decides when image analysis is needed
- ✅ **Conversation flow**: Naturally fits conversational patterns
- ✅ **Error handling**: Agent can retry or ask for better images
- ✅ **Memory integration**: Tool outputs stored in session history
- ⚠️ **Trade-off**: One additional LLM call per image (vs. pre-hook)

**Historical Note:**
Earlier designs explored a pre-hook pattern (processing before agent executes) for faster responses, but the tool pattern provides better agent visibility and more natural conversational flow, making it the preferred choice for production deployments.

---

### 3.3b External MCPTools Pattern (Spoonacular Recipes)

External tools have different requirements:

**External MCPTools Pattern (Spoonacular Recipes):**
- External MCP server (Node.js via npx)
- Registered with `MCPTools(command="...")`
- Agno manages lifecycle automatically
- Startup validation required (fail if unreachable)
- Perfect for: Remote APIs, external services, complex separable processes

**Why This Matters:**  
- Recipe search leverages existing maintained API (no data pipeline)
- Clear separation: Image handling (internal @tool) vs. recipe orchestration (external MCP)
- Detected ingredients automatically part of chat history as text

---

### 3.3c Knowledge Base: Semantic Learning & Troubleshooting

The system includes an optional **knowledge base** for capturing learnings and troubleshooting information.

**Knowledge Base Architecture:**
- **Vector Store**: LanceDB with SentenceTransformer embeddings (lightweight, no API costs)
- **Content Storage**: SQLite for metadata (enables AgentOS platform UI display)
- **Purpose**: Store API errors, troubleshooting findings, edge cases
- **Agent Usage**: Agent can search knowledge for past solutions to similar issues
- **Observability**: Knowledge appears in AgentOS platform's Knowledge tab

**What Gets Stored:**
- API errors and their resolutions (402 quota exceeded, 429 rate limited)
- Failed recipe searches and workarounds
- Edge cases and unexpected inputs
- Performance optimization insights
- User preference patterns

**Why Knowledge Base:**
- ✅ **Agent learning**: Can reference previous solutions without prompting
- ✅ **Debugging**: Developers can search for past issues
- ✅ **Minimal overhead**: SentenceTransformer embeddings (free, local)
- ✅ **Platform integration**: Visible in AgentOS UI for team learning
- ⚠️ **Optional**: Can be disabled for simpler deployments

---

### 3.4 Why Session-Based Memory with Database Persistence


Agno provides **automatic session management** with persistent storage:

**Storage Strategy:**
- **Development**: SQLite + LanceDB (file-based, zero setup)
- **Production**: PostgreSQL + pgvector (configured via DATABASE_URL)
- Sessions persist across restarts
- Automatic FIFO eviction (configurable via MAX_HISTORY)

**Memory Design:**
- Base64 images NEVER stored (only metadata: id, ingredients)
- Chat history stored per session with turn-level metadata
- Preferences extracted and persisted automatically
- Context compression when conversations get long

**Trade-off:**  
File-based storage for dev is ephemeral but simple. PostgreSQL for production requires setup but provides ACID guarantees.

**Why This Matters:**  
- Reviewers can clone and run immediately (no database setup)
- Production deployments use standard database practices
- No custom memory management code needed
- Preferences persist across conversation turns

---

### 3.5 Why Spoonacular MCP (Not RAG Pipeline)

Using external recipe API via MCP instead of building semantic search pipeline:

**Advantages:**
- ✅ Zero data pipeline overhead (no ETL, no vectorization)
- ✅ Always up-to-date recipes (Spoonacular maintains database)
- ✅ Fast implementation with focus on orchestration patterns
- ✅ 50K+ recipes maintained externally
- ✅ Simple MCP integration
- ✅ Minimal infrastructure required

**Trade-offs:**
- ⚠️ External API dependency (requires internet)
- ⚠️ Per-call costs (free tier with limits)
- ⚠️ Less customization than self-hosted database

**Why This Matters:**  
MCP approach provides simplicity and rapid time-to-market. For enterprise deployments with offline requirements or proprietary recipes, a RAG pipeline can be added later without refactoring the agent orchestration layer.

---

### 3.6 Why Dedicated MCP Initialization Module

The Spoonacular MCP requires **proper initialization with connection validation** before the agent starts.

**Architecture: SpoonacularMCP Class (mcp_tools/spoonacular.py)**

**Design Pattern:**
- Dedicated initialization class in `mcp_tools/spoonacular.py`
- Validates API key before attempting connection
- Tests MCP connection with exponential backoff retries
- Initializes MCPTools only after successful validation
- Fails application startup if connection cannot be established

**Initialization Flow:**
1. **API Key Validation**: Check `SPOONACULAR_API_KEY` is present and non-empty
2. **Connection Testing**: Attempt to connect to MCP server (via npx)
3. **Retry Logic**: Exponential backoff (1s → 2s → 4s) for transient failures
4. **Tool Creation**: Initialize MCPTools only after successful connection
5. **Startup Failure**: Raise exception if connection fails after all retries

**Why Dedicated Module:**
- ✅ **Clean separation**: MCP initialization logic isolated from app.py
- ✅ **Reusability**: Easy to add more MCPs with same pattern
- ✅ **Testability**: Can unit test initialization logic independently
- ✅ **Fail-fast**: Application startup fails if external dependency unreachable
- ✅ **Explicit dependencies**: Clear that Spoonacular is required for app to run
- ✅ **Better error messages**: Specific failure reasons (API key invalid, connection timeout, etc.)

**Trade-off:**
Adds one more file (mcp_tools/spoonacular.py), but provides much better error handling and startup validation than inline initialization.

**Why This Matters:**
- External MCP is critical dependency (app cannot function without it)
- Connection issues should fail startup, not first user request
- Retry logic handles transient network issues gracefully
- Clear error messages help developers debug setup issues quickly

---

## 4. High-Level Architecture

### System Overview Diagram

```mermaid
flowchart TD
    CLI[CLI/Postman/curl<br/>Testing] --> AGENTOS[AgentOS<br/>Single Entry Point]
    BROWSER[Web Browser] --> AGENTOS
    
    AGENTOS --> API[Built-in REST API<br/>/api/agents/chat]
    AGENTOS --> UI[Built-in Web UI<br/>AGUI at :7777]
    
    API --> AGENT[Agno Agent<br/>Stateful Orchestrator]
    UI --> AGENT
    
    AGENT --> DB[(SQLite/PostgreSQL<br/>Session Storage)]
    AGENT --> ING_TOOL[@tool decorator<br/>Ingredient Detection<br/>Local]
    AGENT --> REC_MCP[MCPTools<br/>Spoonacular MCP<br/>External]
    
    ING_TOOL --> GEMINI[Gemini Vision API]
    REC_MCP --> SPOON[Spoonacular API<br/>via npx]
```

### Diagram Explanation

- **AgentOS**: Single Python application providing all infrastructure
- **REST API**: Built-in JSON endpoints for programmatic access
- **Web UI (AGUI)**: Built-in ChatGPT-like interface for interactive testing
- **Agno Agent**: Central orchestrator with automatic memory and tool routing
- **Database**: SQLite (dev) or PostgreSQL (prod) for session persistence
- **Ingredient Tool**: Local @tool function calling Gemini vision
- **Recipe MCP**: External Node.js process calling Spoonacular API

**Key Insight:** Everything runs from `python app.py` - no separate servers needed.

### AGUI (Built-in Web Interface)

AgentOS provides AGUI, a production-ready ChatGPT-like web interface at `http://localhost:7777` (or configured PORT). No separate frontend setup required.

**Features:**
- **Interactive Chat UI**: Send messages, upload images, view responses in real-time
- **Session Management**: Automatic session persistence with session_id tracking
- **Chat History Viewer**: Browse previous conversation turns within a session
- **Memory & Preferences Viewer**: Inspect stored user preferences and agent memories
- **Tool Call Transparency**: See which tools were invoked and their outputs
- **Multi-Session Support**: Switch between different conversation threads

**Configuration:**
```python
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

agent_os = AgentOS(
    agents=[agent],
    interfaces=[AGUI(agent=agent)]  # Registers web UI for this agent
)

if __name__ == "__main__":
    agent_os.serve(
        app="app:app",
        port=config.PORT,  # Default 7777
        reload=False       # MCP lifecycle requires reload=False to avoid connection issues
    )
```

**Access:**
- Web UI: `http://localhost:7777`
- REST API: `http://localhost:7777/api/agents/chat`
- OpenAPI Docs: `http://localhost:7777/docs` (automatic Swagger UI)

**Development Workflow:**
1. Start server: `python app.py`
2. Open AGUI in browser for interactive testing
3. Use REST API for programmatic access (CLI/Postman)
4. View tool calls and session state in real-time

---

## 5. Repository & Module Structure

### Folder Structure

```
.
├── app.py                    # Single entry point (AgentOS application, async initialization)
│
├── src/                      # Application source code
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py         # Environment configuration (dotenv + env vars)
│   │   ├── logger.py         # Logging configuration (structured/text, colored output)
│   │   └── tracing.py        # OpenTelemetry tracing setup (AgentOS integration)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py         # Pydantic v2 schemas (ChatMessage, RecipeResponse, etc)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   └── agent.py          # Agent factory function (initialize_recipe_agent, async)
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── prompts.py        # System instructions and dynamic prompts
│   │
│   ├── hooks/
│   │   ├── __init__.py
│   │   └── hooks.py          # Pre-hooks and post-hooks factories
│   │
│   └── mcp_tools/
│       ├── __init__.py
│       ├── ingredients.py    # Ingredient detection @tool (Gemini vision API)
│       └── spoonacular.py    # SpoonacularMCP class with connection validation & retries
│
├── tests/
│   ├── unit/                 # Python unit tests (pytest)
│   │   ├── test_models.py         # Pydantic schema validation
│   │   ├── test_config.py         # Environment configuration loading
│   │   ├── test_logger.py         # Logging output formats
│   │   ├── test_ingredients.py    # Image detection logic
│   │   ├── test_mcp.py            # MCP initialization & retries
│   │   ├── test_app.py            # Application startup validation
│   │   └── test_tracing.py        # Tracing initialization
│   └── integration/               # Agno evals (E2E tests with real APIs)
│       ├── conftest.py            # Pytest configuration and fixtures
│       ├── test_eval.py           # Agno SDK-based evaluations
│       └── test_integration.py    # REST API endpoint tests
│
├── tmp/                      # Runtime artifacts (git-ignored)
│   ├── lancedb/              # LanceDB vector database for knowledge base
│   ├── recipe_agent_sessions.db  # SQLite session storage (optional)
│   └── eval_results.db       # Evaluation metrics and results
│
├── .env.example              # Template environment file (no secrets)
├── .gitignore                # Excludes .env, *.db, tmp/, __pycache__
├── Makefile                  # Build/test/deploy commands
├── requirements.txt          # Python dependencies with versions
├── pytest.ini                # Pytest configuration
├── README.md                 # Project documentation
└── .github/
    └── copilot-instructions.md  # Development guidelines
```

### Module Responsibilities

**app.py** (AgentOS Entry Point - Minimal Orchestration)
- ~50-60 lines: Clean, focused orchestration
- Call async factory: `agent, tracing_db, knowledge = asyncio.run(initialize_recipe_agent())`
- Create AgentOS instance with agent, knowledge base, and tracing
- Extract FastAPI app: `app = agent_os.get_app()`
- Extract FastAPI app: `app = agent_os.get_app()`
- Serve application: `agent_os.serve(app="app:app", port=config.PORT)`
- Logging for startup status and URLs
- Single entry point: `python app.py`

**agent.py** (Agent Factory Function - Async)
- `async def initialize_recipe_agent() -> tuple[Agent, tracing_db, knowledge]` async factory (~240 lines)
- 7-step initialization with detailed logging:
  - Step 1: Spoonacular MCP initialization with fail-fast validation and exponential backoff
  - Step 2: Tracing initialization (OpenTelemetry, optional based on config)
  - Step 3: Database configuration for session persistence (SQLite dev / PostgreSQL prod)
  - Step 2c: Knowledge base initialization (LanceDB vector store + SQLite metadata)
  - Step 4: Tools registration (Spoonacular MCP + optional ingredient detection tool based on IMAGE_DETECTION_MODE)
  - Step 5: Pre-hooks and post-hooks registration (ingredient extraction, guardrails, response formatting)
  - Step 6: Agno Agent configuration with all settings, retries, memory, guardrails
- Imports from: config, logger, models, ingredients, SpoonacularMCP, prompts, hooks, tracing
- Returns: (agent, tracing_db, knowledge) ready for AgentOS
- Async pattern: All I/O operations await properly, including MCP and tracing initialization

**prompts.py** (System Instructions)
- `SYSTEM_INSTRUCTIONS` constant (~800 lines, pure data)
- Comprehensive behavior guidance for agent:
  - Core responsibilities (recipes only)
  - Ingredient source prioritization
  - Two-step recipe process (search → get_recipe_information_bulk)
  - Image handling for pre-hook vs. tool mode
  - Preference extraction and application
  - Edge case handling and critical guardrails
  - Response guidelines and example interactions

**hooks.py** (Pre-Hooks and Post-Hooks Factories)
- `get_pre_hooks() -> List` factory function (~50 lines)
  - Returns list of pre-hooks to register with agent
  - Ingredient extraction pre-hook (when IMAGE_DETECTION_MODE="pre-hook")
  - Prompt injection guardrail (always enabled)
  - Configuration-driven based on IMAGE_DETECTION_MODE
- `get_post_hooks() -> List` factory function (~30 lines)
  - Returns list of post-hooks to register with agent
  - Response field extraction for UI rendering (extracts 'response' from RecipeResponse)
  - Error recovery and formatting hooks
- Structured logging for hook registration
- Both factories return empty lists if conditions not met (graceful degradation)

**config.py** (Configuration)
- Load .env file using python-dotenv
- System environment variables override .env values
- Provide typed Config object with defaults
- Validate required fields (GEMINI_API_KEY, SPOONACULAR_API_KEY)
- Export constants (MAX_HISTORY, MAX_IMAGE_SIZE_MB, MIN_INGREDIENT_CONFIDENCE)
- Export IMAGE_DETECTION_MODE (pre-hook vs. tool)

**logger.py** (Logging Configuration)
- Configure Python logging with structured or text output
- Support LOG_LEVEL env var (DEBUG, INFO, WARNING, ERROR)
- Support LOG_TYPE env var (json, text) - default: text
- Text format: Rich formatted output with colors and icons
- JSON format: Structured JSON for log aggregation and parsing
- Export configured logger instance for import by all modules
- Never log sensitive data (API keys, full images, passwords)

**models.py** (Pydantic v2 Schemas with Field Constraints)
- **Input schema: RecipeRequest**
  - `ingredients`: List[str] with constraints min_length=1, max_length=50 (1-50 ingredient items)
  - Field validator on ingredients list: Ensure non-empty strings, max 100 chars each
  - Optional fields: diet, cuisine, meal_type, intolerances (each 1-100 chars if provided)
  - ConfigDict: Auto-strip whitespace from all string fields
- **Output schema: RecipeResponse**
  - `response`: Required string (1-5000 chars) - LLM-generated conversational response
  - `recipes`: List[Recipe] with max_length=50 (up to 50 recipe objects)
  - `ingredients`: List[str] with max_length=100 (detected/provided ingredients)
  - `execution_time_ms`: int with constraints ge=0, le=300000 (0-5 minutes)
  - Optional fields: reasoning, session_id, run_id (each 1-100 chars if provided)
  - ConfigDict: Auto-strip whitespace from all string fields
- **Domain model: Recipe**
  - `title`: str (1-200 chars)
  - `ingredients`: List[str] with constraints min_length=1, max_length=100
  - `instructions`: List[str] with constraints min_length=1, max_length=100
  - `prep_time_min`, `cook_time_min`: int with constraints ge=0, le=1440 (0-24 hours)
  - `source_url`: Optional str with pattern validation (must start with http:// or https://)
  - Model validator: Ensure total cooking time (prep + cook) ≤ 1440 minutes
  - ConfigDict: Auto-strip whitespace
- **Domain model: Ingredient**
  - `name`: str (1-100 chars)
  - `confidence`: float with constraints ge=0.0, le=1.0 (inclusive, allows boundaries)
  - ConfigDict: Auto-strip whitespace
- **Domain model: IngredientDetectionOutput**
  - `ingredients`: List[str] with constraints min_length=1, max_length=50
  - `confidence_scores`: dict[str, float] with field validator enforcing 0.0 < score < 1.0 (exclusive)
  - Model validator: Ensure all ingredients have confidence scores
  - Optional field: image_description (max 500 chars)
  - ConfigDict: Auto-strip whitespace

**Validation Architecture:**
- Use `Annotated[Type, Field(...)]` for declarative constraints (ranges, lengths, patterns)
- Field constraints: ge/le (inclusive), gt/lt (exclusive), min_length, max_length, pattern
- Custom validators: Only for cross-field validation or complex logic (mode='after')
- ConfigDict with str_strip_whitespace=True: Automatic whitespace trimming on all strings
- Distinction: Ingredient.confidence uses inclusive (ge/le) 0.0-1.0; IngredientDetectionOutput.confidence_scores uses exclusive (gt/lt) 0.0-1.0

**mcp_tools/spoonacular.py** (MCP Initialization)
- SpoonacularMCP class with initialization logic
- API key validation (check presence and format)
- Connection testing with retry logic (exponential backoff: 1s → 2s → 4s)
- MCPTools creation only after successful connection
- Fail-fast on startup if connection cannot be established

**ingredients.py** (Ingredient Detection)
- Core helper functions (reusable for both pre-hook and tool modes)
- Pre-hook function: `extract_ingredients_pre_hook(run_input, ...)`
- Tool function: `detect_ingredients_tool(image_data: str)`
- Shared core functions: fetch_image_bytes, validate_image, extract_ingredients_from_image
- Retry logic with exponential backoff

**tests/** (Test Suite - 140+ tests)
- Unit tests: Models, config, logging, MCP, ingredients, app (fast, isolated)
- Integration tests: E2E flows with real APIs (requires keys)

### Architectural Pattern: Factory + Separation of Concerns

**Design Principle:** Each module has a single, focused responsibility.

- **app.py**: Orchestration (minimal ~50 lines)
- **agent.py**: Agent initialization (factory pattern)
- **prompts.py**: Behavior definition (system instructions)
- **hooks.py**: Pre-hook configuration (factory pattern)
- **config.py**: Environment and validation
- **logger.py**: Structured logging
- **models.py**: Data validation (Pydantic)
- **ingredients.py**: Image processing
- **mcp_tools/spoonacular.py**: MCP initialization

**Benefits:**
- ✅ **Modular**: Clear purpose for each file
- ✅ **Testable**: Easy to unit test each module
- ✅ **Maintainable**: Changes isolated to specific files
- ✅ **Readable**: Clear dependencies between modules
- ✅ **Reusable**: Core functions usable in multiple contexts
- ✅ **AgentOS Compatible**: No breaking changes to runtime behavior

---

## 6. AgentOS Application Design (app.py)

### Application Structure

app.py is the **complete application** in ~150-200 lines:

**1. Import Dependencies**
```python
from agno.agent import Agent
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from agno.tools import tool
from agno.models.google import Gemini
from agno.db.sqlite import SqliteDb
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from pydantic import BaseModel
from typing import List, Optional
import base64
from src.utils.config import config
from src.mcp_tools.spoonacular import SpoonacularMCP
from src.mcp_tools.ingredients import extract_ingredients_pre_hook
from src.utils.logger import logger
```

**2. Define Schemas**
```python
class RecipeRequest(BaseModel):
    ingredients: List[str]
    diet: Optional[str] = None
    cuisine: Optional[str] = None
    meal_type: Optional[str] = None

class Recipe(BaseModel):
    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    prep_time_min: int
    cook_time_min: int

class RecipeResponse(BaseModel):
    recipes: List[Recipe]
    ingredients: List[str]
    preferences: dict[str, str]
```

**3. Define Pre-Hook for Ingredient Extraction**

Create a separate `src/mcp_tools/ingredients.py` module:

```python
# src/mcp_tools/ingredients.py
from agno.run.agent import RunInput
import base64
import imghdr
import google.generativeai as genai
from src.utils.config import config

def extract_ingredients_pre_hook(
    run_input: RunInput,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """
    Pre-hook: Extract ingredients from image before agent executes.
    
    - Detects if request contains images
    - Calls Gemini vision API to extract ingredients
    - Filters by MIN_INGREDIENT_CONFIDENCE
    - Appends extracted ingredients to user message as clean text
    - Clears images from input to prevent agent re-processing
    """
    # Check if images exist in request
    images = getattr(run_input, 'images', [])
    if not images:
        return  # No image, skip
    
    detected_ingredients = []
    
    for image in images:
        try:
            # Get image bytes (URL or content)
            if image.url:
                image_bytes = fetch_image_from_url(image.url)
            elif image.content:
                image_bytes = image.content
            else:
                continue
            
            # Validate format and size
            image_type = imghdr.what(None, h=image_bytes)
            if image_type not in ['jpeg', 'png']:
                raise ValueError(f"Invalid format: {image_type}")
            
            size_mb = len(image_bytes) / (1024 * 1024)
            if size_mb > config.MAX_IMAGE_SIZE_MB:
                raise ValueError(f"Image too large: {size_mb:.2f}MB")
            
            # Call Gemini vision API
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            
            mime_type = f"image/{image_type}"
            response = model.generate_content([
                "Extract all food ingredients from this image. Return JSON with 'ingredients' list and 'confidence_scores' dict.",
                {"mime_type": mime_type, "data": image_bytes}
            ])
            
            # Parse response and filter by confidence
            result = parse_json(response.text)
            filtered = [
                ing for ing, conf in result.get('confidence_scores', {}).items()
                if conf >= config.MIN_INGREDIENT_CONFIDENCE
            ]
            detected_ingredients.extend(filtered)
            
        except Exception as e:
            log.warning(f"Image processing failed: {e}, continuing with user input")
            continue
    
    # Append detected ingredients to message (not the image)
    if detected_ingredients:
        ing_text = ", ".join(detected_ingredients)
        run_input.input_content = (
            f"{run_input.input_content}\n\n"
            f"[Detected Ingredients] {ing_text}"
        )
        
        # Clear images to prevent agent re-processing
        run_input.images = []
```

**4. Initialize Spoonacular MCP with Connection Validation**
```python
# Initialize MCP before creating agent (fail-fast if unreachable)
# IMPORTANT: This is an async operation called at module-level with asyncio.run()
logger.info("Initializing Spoonacular MCP...")
spoonacular_mcp = SpoonacularMCP(
    api_key=config.SPOONACULAR_API_KEY,
    max_retries=3,
    retry_delays=[1, 2, 4]  # Exponential backoff (uses asyncio.sleep, not time.sleep)
)

try:
    # This will validate API key and test connection asynchronously
    # Retry delays are non-blocking (async), allowing concurrent initialization
    mcp_tools = await spoonacular_mcp.initialize()  # async method, awaited
    logger.info("Spoonacular MCP initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Spoonacular MCP: {e}")
    raise SystemExit(1)  # Fail startup
```

**5. Create Agno Agent with Advanced Features**
```python
agent = Agent(
    model=Gemini(
        id=config.GEMINI_MODEL,
        retries=2,                      # Automatic retry on failures
        delay_between_retries=1,        # Initial delay in seconds
        exponential_backoff=True        # Doubles delay on each retry
    ),
    db=SqliteDb(db_file="agno.db"),     # Or PostgreSQL via config.DATABASE_URL
    
    # Memory configuration
    add_history_to_context=True,        # Include chat history automatically
    num_history_runs=config.MAX_HISTORY,  # Last N conversation turns
    enable_user_memories=True,          # Store preferences across sessions
    enable_session_summaries=True,      # Auto-summarize long conversations
    
    # Context compression
    compress_tool_results=True,         # Compress after 3 tool calls
    
    # Structured I/O
    input_schema=RecipeRequest,         # Validate request structure
    output_schema=RecipeResponse,       # Pydantic validation
    
    # Guardrails
    pre_hooks=[
        extract_ingredients_pre_hook,          # Image detection (runs first)
        PIIDetectionGuardrail(mask_pii=True),  # Mask sensitive info
        PromptInjectionGuardrail()             # Block prompt attacks
    ],
    
    # Tools
    tools=[
        mcp_tools  # Initialized MCPTools from SpoonacularMCP.initialize()
    ],
    
    # System instructions (detailed behavior guidance)
    instructions="""
    You are a recipe recommendation agent. You ONLY answer recipe-related questions.
    
    TOOL USAGE:
    1. search_recipes: Call when ingredients available and recipes requested
    2. get_recipe_information_bulk: Get full details after search (REQUIRED - never invent recipes)
    
    DECISION FLOW:
    1. Check if recipe-related (refuse if not)
    2. Determine ingredient source: [Detected Ingredients] → user_message → history
    3. Extract preferences: diet, cuisine, meal_type, intolerances
    4. Call tools as needed (search → get_recipe_information_bulk)
    5. Ground responses in tool outputs only (no hallucinations)
    """
)
```

**6. Create AgentOS and Serve**
```python
# Module-level initialization (factory function is async)
import asyncio

# Step 1: Call async factory function to initialize agent
# This runs all async initialization (MCP connection, database setup)
# Retry delays during MCP init are non-blocking (asyncio.sleep)
from src.agents.agent import initialize_recipe_agent

agent = asyncio.run(initialize_recipe_agent())  # Async startup completes before serving

# Step 2: Create AgentOS (handles everything)
agent_os = AgentOS(
    agents=[agent],
    interfaces=[AGUI(agent=agent)]
)

# Get FastAPI app (with built-in routes)
app = agent_os.get_app()

if __name__ == "__main__":
    # Single command: python app.py
    # Serves REST API at http://localhost:PORT (configurable via environment)
    # Serves Web UI at http://localhost:PORT
    # Manages MCP automatically
    
    # IMPORTANT: Do NOT use reload=True with MCP tools
    # It causes lifespan management issues with external MCP connections
    # For development, manually restart the process when code changes
    agent_os.serve(app="app:app", port=config.PORT)
```

**Async Startup Design Pattern:**
- `initialize_recipe_agent()` is `async def` (awaits MCP init and database setup)
- `asyncio.run()` creates event loop, waits for async initialization to complete
- Retry delays during MCP connection use `asyncio.sleep()` (non-blocking)
- After startup completes, AgentOS serves synchronously (no async in request handlers)
- This pattern: **Async initialization → Synchronous serving**

### Key Implementation Points

**What You Write:**
- Input/output schemas (Pydantic models)
- Local ingredient detection tool (@tool function)
- Agent configuration (model, database, memory, guardrails)
- System instructions (detailed behavior guidance)
- AgentOS setup (agents + interfaces)

**What AgentOS Provides:**
- REST API endpoints (automatic)
- Web UI interface (AGUI)
- Session management (automatic per session_id)
- Memory persistence (SQLite/PostgreSQL)
- Tool lifecycle (MCP startup, connections)
- Error handling and logging
- Built-in tracing and evals

**Result:** ~150-200 lines vs. ~950 lines with custom implementation.

---

## 7. Data Flow & Request Lifecycle

### High-Level Flow

```mermaid
sequenceDiagram
    participant C as Client<br/>(REST API or Web UI)
    participant A as AgentOS<br/>(Built-in Layer)
    participant AG as Agno Agent<br/>(Orchestrator)
    participant DB as Database<br/>(SQLite/PostgreSQL)
    participant ING as @tool<br/>extract_ingredients
    participant REC as MCPTools<br/>Spoonacular

    C->>A: POST /api/agents/chat<br/>{message, image_base64, session_id}
    A->>A: Validate input (format, size)
    A->>AG: Route to agent.run()
    AG->>DB: Retrieve session history
    AG->>AG: Apply guardrails
    AG->>AG: Determine ingredient source
    
    alt Image present
        AG->>ING: extract_ingredients(image_base64)
        ING->>ING: Call Gemini vision API
        ING->>ING: Filter by confidence
        ING-->>AG: {ingredients, description, filtered}
    end
    
    alt Ingredients available
        AG->>REC: search_recipes(ingredients, preferences)
        REC->>REC: Call Spoonacular API
        REC-->>AG: {recipe_ids[]}
        AG->>REC: get_recipe_information_bulk(ids)
        REC-->>AG: {recipes[]}
    end
    
    AG->>AG: Synthesize response
    AG->>DB: Store conversation turn
    AG-->>A: {response, recipes, ingredients, metadata}
    A-->>C: JSON response
```

### Detailed Step-by-Step

**1. Request arrives at AgentOS (Built-in Layer)**
- Validate JSON structure against input_schema
- Check image format (JPEG/PNG) if provided
- Decode base64 if provided
- Check image size (return 413 if > MAX_IMAGE_SIZE_MB)
- Generate session_id if missing
- AgentOS handles all validation automatically

**2. AgentOS routes to Agno Agent**
- Call `agent.run(message, session_id=session_id)`
- Agno loads session history from database automatically
- Agno applies num_history_runs context window

**3. Pre-hook extracts ingredients (if image provided)**
- Pre-hook function runs BEFORE agent processes request
- Checks if images in `run_input`
- Calls Gemini vision API to extract ingredients (one call only)
- Filters by MIN_INGREDIENT_CONFIDENCE
- **Appends detected ingredients to user message as clean text**
- Clears images from input to prevent agent re-processing
- Agent receives: "What recipes?\n\n[Detected Ingredients] tomato, basil, mozzarella"

**4. Agno Agent processes enriched request**
- Apply additional pre-hooks (guardrails: PII, prompt injection)
- Parse enriched user_message for ingredients and preferences
- Determine ingredient source priority:
  1. Explicit ingredients appended by pre-hook (from image)
  2. Ingredients in user_message text
  3. Ingredients from session history
- If no ingredients available → refuse with helpful message

**5. Agno Agent calls recipe MCP (conditional)**
- Only if ingredients available AND recipes requested
- Two-step process (via system instructions):
  - Step 1: `search_recipes(query=ingredients, diet, cuisine, intolerances, type, number)`
  - Step 2: `get_recipe_information_bulk(ids=recipe_ids)`
- Extract preferences from user_message or session memory
- Agno passes preferences as tool parameters automatically
- MCP returns full recipe details
- **No vision tool needed** - agent only processes clean ingredient text

**6. Agno Agent synthesizes response**
- Ground response in tool outputs (no hallucinations)
- Reference chat history naturally
- Mention preferences and context
- Validate against output_schema (RecipeResponse)
- Apply context compression if needed (after 3+ tool calls)

**7. Agno Agent stores conversation turn**
- Store user message (with appended ingredients) + assistant response
- Store metadata: ingredients, preferences, tools called
- Chat history includes extracted ingredients as **text, not image bytes**
- Apply FIFO eviction if MAX_HISTORY exceeded
- Database persistence (automatic)

**8. AgentOS returns response**
- Format response according to output_schema
- Include metadata: tools_called, model_used, response_time_ms
- Return via REST API (JSON) or render in Web UI

---

## 8. Session & Memory Management

### Agno Built-in Memory

Agno provides **automatic session management** - no custom code needed.

**Configuration:**
```python
agent = Agent(
    db=SqliteDb(db_file="agno.db"),  # Or PostgreSQL
    add_history_to_context=True,
    num_history_runs=3,              # Last 3 turns
    enable_user_memories=True,       # Persistent preferences
    enable_session_summaries=True,   # Auto-summarization
)
```

**What Gets Stored Automatically:**
- User messages and assistant responses
- Tool calls and results
- Session metadata (preferences, context)
- Conversation summaries (when long)

**What NEVER Gets Stored:**
- Base64 image data (only metadata: id, ingredients)
- Raw image bytes (privacy/memory optimization)

**Memory Lifecycle:**
1. Client provides `session_id` (or Agno generates one)
2. Agno loads last N turns (configurable via num_history_runs)
3. Agent processes with full context
4. Agno stores new turn automatically
5. Agno applies FIFO eviction if MAX_HISTORY exceeded
6. Agno compresses context if needed (after N tool calls)

**Session Persistence:**
- Development: SQLite file (agno.db) + LanceDB for vectors
- Production: PostgreSQL via DATABASE_URL (recommended for scale)
- Sessions persist across restarts
- Same session_id = same conversation

**Image Memory in Chat History:**

⚠️ **Important Design Note:** Agno stores chat history as text (messages and tool outputs), not images.

When a user uploads an image in turn 1:
1. `extract_ingredients()` processes the image and returns text: `["tomato", "basil", "mozzarella"]`
2. This text output is stored in chat history automatically
3. In turn 2 (follow-up message), the image itself is NOT re-transmitted
4. But the extracted ingredients from turn 1 ARE in the history

**Critical:** Ensure `extract_ingredients()` returns a clear, descriptive text list so the agent "remembers" what was in the image:
- ✅ Good: `"image_description": "Fresh tomatoes, basil, and mozzarella on wooden table"`
- ✅ Good: `"ingredients": ["tomato", "basil", "mozzarella"]`
- ❌ Avoid: Generic descriptions that lose context

The agent's context window for follow-ups will include:
- User's original message from turn 1 (with image reference)
- Tool output from `extract_ingredients` (detailed text description + ingredient list)
- User's follow-up message in turn 2
- BUT NOT the actual image bytes/data

This is by design: text-based history is efficient and sufficient for follow-up recipes based on already-identified ingredients.

**Database Strategy:**

For development (default, zero setup):
```python
from agno.db.sqlite import SqliteDb
from agno.vectordb.lancedb import LanceDb

# Session storage (chat history, metadata)
db = SqliteDb(db_file="tmp/agno.db")

# Vector storage (optional, for knowledge base/RAG if needed)
vector_db = LanceDb(
    table_name="recipe_knowledge",
    uri="tmp/lancedb",  # File-based, local storage
)
```

For production (PostgreSQL + pgvector):
```python
from agno.db.postgres import PostgresDb
from agno.vectordb.pgvector import PgVector

# Unified database for both sessions and vectors
db_url = "postgresql+psycopg://user:pass@host:5432/recipe_db"

db = PostgresDb(db_url=db_url)
vector_db = PgVector(db_url=db_url, table_name="recipe_knowledge")
```

**Key Points:**
- SQLite + LanceDB: File-based, no external dependencies, perfect for development
- PostgreSQL + pgvector: Scalable, ACID compliant, recommended for production
- Switch backends via config only, no code changes needed

**Context Compression:**
```python
agent = Agent(
    compress_tool_results=True,
    # Note: compress_tool_results_limit parameter not confirmed in Agno docs
    # Default behavior: compresses after 3 tool calls automatically
)
```
- Automatically summarizes tool results
- Preserves key facts (numbers, dates, entities)
- Dramatically reduces token usage
- Transparent to application code
- Default threshold: 3 tool calls (built-in behavior)

**Key Simplification:** No custom memory management code. Agno handles everything.

---

## 9. Tool Integration Patterns

### Pattern 1: Local @tool (Ingredient Detection)

**Use Case:** Local operations, vision API calls, synchronous tasks.

**Implementation:**
```python
import base64
import imghdr
from agno.tools import tool
from src.utils.config import config
import google.generativeai as genai

### Pattern 1: Pre-Hook for Ingredient Extraction (Current Implementation)

**Use Case:** Request preprocessing, image handling, data enrichment before agent execution.

**Implementation (ingredients.py):**

```python
from agno.run.agent import RunInput
import google.generativeai as genai
from src.utils.config import config

def extract_ingredients_pre_hook(
    run_input: RunInput,
    session=None,
    user_id: str = None,
    debug_mode: bool = None,
) -> None:
    """Pre-hook: Extract ingredients from images before agent processes request."""
    
    images = getattr(run_input, 'images', [])
    if not images:
        return
    
    detected_ingredients = []
    
    for image in images:
        try:
            # Get image bytes
            if image.url:
                image_bytes = fetch_image_from_url(image.url)
            elif image.content:
                image_bytes = image.content
            else:
                continue
            
            # Validate format and size
            validate_image(image_bytes)
            
            # Call Gemini vision API ONCE
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            response = model.generate_content([
                "Extract food ingredients. Return JSON with 'ingredients' list and 'confidence_scores' dict.",
                {"mime_type": f"image/jpeg", "data": image_bytes}
            ])
            
            # Filter by confidence
            result = parse_json(response.text)
            filtered = [
                ing for ing, conf in result['confidence_scores'].items()
                if conf >= config.MIN_INGREDIENT_CONFIDENCE
            ]
            detected_ingredients.extend(filtered)
            
        except Exception as e:
            log.warning(f"Image processing failed: {e}")
            continue
    
    # Append detected ingredients to user message
    if detected_ingredients:
        ing_text = ", ".join(detected_ingredients)
        run_input.input_content = (
            f"{run_input.input_content}\n\n"
            f"[Detected Ingredients] {ing_text}"
        )
        # Clear images to prevent agent re-processing
        run_input.images = []
```

**Registration in app.py:**

```python
from src.mcp_tools.ingredients import extract_ingredients_pre_hook

agent = Agent(
    model=Gemini(id="gemini-1.5-flash"),
    db=SqliteDb(db_file="agno.db"),
    pre_hooks=[extract_ingredients_pre_hook],  # ← Pre-hook for images
    tools=[
        MCPTools(command="npx -y spoonacular-mcp")  # ← Only recipe search
    ],
)
```

**Characteristics:**
- Lives in separate `ingredients.py` module
- Runs BEFORE agent executes
- Has access to `RunInput` (includes images)
- Calls Gemini vision API once, then appends to message
- Agent receives clean text, not images
- No tool call overhead or agent routing logic needed
- Image bytes NEVER stored; ingredients stored as text in history
- Validation: format, size, and confidence filtering

**When to Use Pre-Hook Pattern:**
- ✅ Request preprocessing (image → ingredients)
- ✅ Need to eliminate LLM round-trip
- ✅ Agent doesn't need visibility into image analysis
- ✅ Cleaner separation of concerns
- ✅ Faster response times

**Alternative: Move to @tool Decorator**

If you need agent-side visibility for refinement:

```python
@tool
def extract_ingredients(image_base64: str) -> dict:
    """Agent-callable tool for ingredient extraction"""
    # ... implementation
```

This requires adding tool routing logic to system instructions and costs one extra LLM call, but provides full agent flexibility.

---

### Pattern 2: External MCPTools (Spoonacular Recipes)

**Use Case:** Remote APIs, external services, complex separable processes.

**Registration:**
```python
from agno.tools.mcp import MCPTools

agent = Agent(
    tools=[
        MCPTools(command="npx -y spoonacular-mcp")  # Correct npm package name
    ],
)
```

**Characteristics:**
- External Node.js process
- Runs via npx (no repo checkout needed)
- Agno manages lifecycle automatically
- Startup validation REQUIRED (fail if unreachable)
- Stateless (no memory between calls)

**Available Tools (provided by spoonacular-mcp):**
- `search_recipes`: Search by ingredients/preferences
  - Parameters: query, diet, cuisine, intolerances, type, number
  - Returns: Recipe IDs and basic info
- `get_recipe_information_bulk`: Get full details for recipe IDs
  - Parameters: ids (comma-separated)
  - Returns: Complete recipe objects with instructions, ingredients, nutrition

**Critical: Two-Step Recipe Process (Anti-Hallucination Safeguard)**

The recipe recommendation flow is strictly two-step to prevent LLM hallucination:

1. **Step 1: search_recipes** → Get recipe IDs
   - Returns metadata (title, readyInMinutes, servings) but NOT instructions
   
2. **Step 2: get_recipe_information_bulk** → Get authoritative details
   - Returns complete instructions, ingredients, nutrition from Spoonacular
   - **Only source of truth for recipe instructions**

**LLM Guardrail:** The system instructions explicitly forbid generating recipe instructions without calling `get_recipe_information_bulk`:
- ⚠️ Never present shortened recipes or inferred instructions
- ⚠️ Always fetch full details before responding to user
- ⚠️ Spoonacular is the authoritative source; never improvise or assume

This two-step approach prevents:
- Hallucinated ingredient lists (use Spoonacular's authoritative list)
- Made-up cooking instructions (use Spoonacular's verified steps)
- Inconsistent recipe information (always from same source)

**System Instructions Guide Tool Usage:**
```
When user requests recipes:
1. Call search_recipes with ingredients and preferences
2. Get recipe IDs from search results
3. Call get_recipe_information_bulk with IDs for full details
4. Present recipes with complete information

CRITICAL: You are FORBIDDEN from generating recipe instructions 
unless you have successfully called get_recipe_information_bulk 
for that specific recipe ID.
```

**No schemas needed in app.py** - spoonacular-mcp defines them via MCP protocol.

---

### Startup Validation

**Only external MCPs require validation:**

```python
# AgentOS handles this automatically during startup
# If Spoonacular MCP unreachable, app fails to start
# No custom validation code needed

# Implicit validation on AgentOS.serve()
agent_os.serve(app="app:app")
# ↑ This fails if MCP connection cannot be established
```

**Local @tool functions need no validation** - they're just Python functions.

---

## 10. Agent Decision Logic & System Instructions

### System Instructions (Detailed Guidance)

The agent's behavior is defined through **system instructions**, not code. Vision (image processing) is handled automatically by the pre-hook before the agent sees the request.

```python
instructions = """
You are a recipe recommendation assistant. You ONLY answer recipe-related questions.

CORE PRINCIPLES:
- Only respond to recipe-related queries. Politely decline off-topic requests.
- Ground ALL responses in tool outputs. Never invent ingredients or recipes.
- Maintain conversation context and user preferences across turns.
- Be helpful, concise, and friendly.

INGREDIENT SOURCES (in priority order):
1. **Pre-detected ingredients**: If message contains [Detected Ingredients] section, use them directly.
   - Example: User uploads image → pre-hook extracts → message includes "[Detected Ingredients] tomato, basil"
2. **Explicit mention**: Ingredients explicitly mentioned in user message
   - Example: "I have tomatoes, basil, and mozzarella"
3. **Conversation history**: Ingredients from previous turns in same session
   - Example: "What about vegetarian options?" (remembers previous image ingredients)

TOOL USAGE GUIDELINES:

1. search_recipes (Spoonacular MCP):
   - CALL when user asks for recipes AND ingredients are available
   - Use TWO-STEP PROCESS (STRICTLY ENFORCED):
     a. First call search_recipes to get recipe IDs
     b. Then call get_recipe_information_bulk with IDs for full details
   - Extract preferences from user message: diet, cuisine, intolerances, type
   - Use parameters: query (ingredients), diet, cuisine, intolerances, type, number
   - ⚠️ **CRITICAL:** Do NOT generate or infer recipe instructions unless you have 
     successfully called get_recipe_information_bulk for that specific recipe ID.
     Only Spoonacular has authoritative recipe details.
   
2. get_recipe_information_bulk (Spoonacular MCP):
   - CALL immediately after search_recipes with recipe IDs
   - Get complete recipe details: title, instructions, ingredients, nutrition
   - Present full recipes to user
   - NEVER present incomplete recipes or shortened versions without this call

DECISION FLOW:
1. Check if request is recipe-related. If not, politely decline.
2. Check for ingredients (in priority order):
   a. [Detected Ingredients] section in message (from pre-hook image processing)
   b. Ingredients explicitly mentioned in current message
   c. Ingredients from previous conversation history
3. If NO ingredients from any source, ask user to provide ingredients or image.
4. When ingredients available and user wants recipes, use TWO-STEP process:
   - Step 1: search_recipes(query, diet, cuisine, intolerances, type, number)
   - Step 2: get_recipe_information_bulk(ids)
5. For follow-ups, preserve previous preferences but allow updates.
6. Always ground responses in tool outputs and reference history naturally.

PREFERENCE EXTRACTION EXAMPLES:
- "Italian vegetarian recipes" → diet="vegetarian", cuisine="italian"
- "Gluten-free dessert ideas" → intolerances="gluten", type="dessert"
- "Quick vegan lunch" → diet="vegan", type="main course"
- "No peanuts please" → intolerances="peanuts"

EDGE CASES:
- Image already processed (ingredients in message): Use [Detected Ingredients] section
- Recipe request without ingredients: Ask for ingredients or image
- Preference changes: Update and apply to new search
- "More options": Call search_recipes again with same/similar parameters
"""
```

### Decision Flow Diagram

```mermaid
flowchart TD
    START[Receive User Message<br/>with possible [Detected Ingredients]]
    GUARD{Recipe-related?}
    
    GUARD -->|No| REFUSE[Return guardrail:<br/>'I help with recipes only']
    GUARD -->|Yes| CHECK_ING{Ingredients<br/>available?}
    
    CHECK_ING -->|In [Detected Ingredients]| PREF[Extract preferences]
    CHECK_ING -->|In message| PREF
    CHECK_ING -->|In history| PREF
    CHECK_ING -->|None| ASK[Ask for ingredients/image]
    
    PREF --> RECIPE{User wants<br/>recipes?}
    RECIPE -->|Yes| SEARCH[Call search_recipes<br/>with preferences]
    RECIPE -->|No| RESPOND[Conversational response]
    
    SEARCH --> BULK[Call get_recipe_information_bulk<br/>with IDs]
    BULK --> RESPOND
    
    ASK --> END[Return to user]
    REFUSE --> END
    RESPOND --> STORE[Store conversation turn<br/>with ingredients as text]
    STORE --> END
```

### Key Points

**Agno Agent handles automatically:**
- Loading session history
- Applying guardrails (pre-hooks)
- Deciding which tools to call
- Extracting preferences from messages
- Passing parameters to tools
- Synthesizing responses from tool outputs
- Storing conversation turns
- Context compression when needed

**You define:**
- System instructions (detailed behavior guidance)
- Input/output schemas (Pydantic validation)
- Tool implementations (local @tool functions)
- Tool registrations (MCPTools connections)

**Result:** Declarative behavior specification instead of imperative orchestration code.

---

## 11. Configuration Management (config.py)

### Design Approach

**Load Priority:** System environment variables > .env file > defaults

**Implementation:**
```python
from dotenv import load_dotenv
import os
from typing import Optional

# Load .env file (if exists)
load_dotenv()

class Config:
    """Application configuration with environment variable support."""
    
    # Required API keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SPOONACULAR_API_KEY: str = os.getenv("SPOONACULAR_API_KEY", "")
    
    # Model configuration
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Server configuration
    PORT: int = int(os.getenv("PORT", "7777"))
    
    # Memory settings
    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "3"))
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
    MIN_INGREDIENT_CONFIDENCE: float = float(os.getenv("MIN_INGREDIENT_CONFIDENCE", "0.7"))
    
    # Database (optional - defaults to SQLite + LanceDB)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")  # For PostgreSQL in production
    
    def validate(self):
        """Validate required configuration."""
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        if not self.SPOONACULAR_API_KEY:
            raise ValueError("SPOONACULAR_API_KEY is required")

# Create and validate config
config = Config()
config.validate()
```

### Environment Variables

**Required:**
- `GEMINI_API_KEY` - Gemini API key for vision model
- `SPOONACULAR_API_KEY` - Spoonacular API key for recipes

**Optional (with defaults):**
- `GEMINI_MODEL=gemini-1.5-flash` - Model name
- `PORT=7777` - Server port for REST API and Web UI
- `MAX_HISTORY=3` - Maximum conversation turns to keep
- `MAX_IMAGE_SIZE_MB=5` - Maximum image upload size
- `MIN_INGREDIENT_CONFIDENCE=0.7` - Confidence threshold for ingredients
- `DATABASE_URL` - PostgreSQL connection string (uses SQLite+LanceDB if not set)

**Note:** For production PostgreSQL, use format: `postgresql+psycopg://user:pass@host:5432/dbname`

### Repository Files

**.env.example** (committed):
```bash
# Required
GEMINI_API_KEY=your_gemini_key_here
SPOONACULAR_API_KEY=your_spoonacular_key_here

# Optional (defaults shown)
GEMINI_MODEL=gemini-1.5-flash
MAX_HISTORY=3
MAX_IMAGE_SIZE_MB=5
MIN_INGREDIENT_CONFIDENCE=0.7

# Optional (production)
DATABASE_URL=postgresql://user:pass@host:5432/recipe_db
```

**.env** (gitignored):
```bash
# Developer's actual credentials
GEMINI_API_KEY=actual_key_here
SPOONACULAR_API_KEY=actual_key_here
```

**.gitignore:**
```
.env
*.db
*.lance
__pycache__/
```

---

## 12. Logging Configuration (logger.py)

### Design Approach

Centralized logging configuration supporting both structured JSON and rich text output with colors.

**Features:**
- Configurable log level via `LOG_LEVEL` environment variable
- Configurable output format via `LOG_TYPE` environment variable
- Rich text format with colors and icons (default)
- JSON format for log aggregation and parsing
- Never logs sensitive data (API keys, images, passwords)
- Logs request metadata for debugging (IDs, times, tool calls)

**Environment Variables:**
- `LOG_LEVEL` (default: INFO) - DEBUG, INFO, WARNING, ERROR
- `LOG_TYPE` (default: text) - text (rich, colored), json (structured)

**Implementation:**

```python
import logging
import json
import sys
from typing import Any, Dict
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        
        return json.dumps(log_data)

class RichTextFormatter(logging.Formatter):
    """Rich text formatter with colors and icons."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
    }
    
    ICONS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
    }
    
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname
        color = self.COLORS.get(level, "")
        icon = self.ICONS.get(level, "")
        
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        msg = f"{color}{icon} [{timestamp}] {level:8} {record.name:20} {record.getMessage()}{self.RESET}"
        
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg

def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance."""
    
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger  # Already configured
    
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_type = os.getenv("LOG_TYPE", "text").lower()
    
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    handler = logging.StreamHandler(sys.stdout)
    
    if log_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = RichTextFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger

# Module logger for import
logger = get_logger("recipe_service")
```

**Usage:**
```python
from src.utils.logger import logger, get_logger

# Module-level logger
logger.info("Application starting")
logger.warning("Image size approaching limit", extra={"session_id": "abc123"})
logger.error("Failed to extract ingredients", extra={"request_id": "req_456"})

# Function-specific logger
def process_image():
    func_logger = get_logger("recipe_service.ingredients")
    func_logger.debug("Processing image bytes")
```

---

## 13. Data Models (models.py)

### API Schemas

```python
from pydantic import BaseModel
from typing import List, Optional

class RecipeRequest(BaseModel):
    """Input schema for recipe requests."""
    ingredients: List[str]
    diet: Optional[str] = None          # vegetarian, vegan, gluten-free, etc.
    cuisine: Optional[str] = None       # italian, mexican, chinese, etc.
    meal_type: Optional[str] = None     # main course, dessert, appetizer, etc.
    intolerances: Optional[str] = None  # comma-separated

class Recipe(BaseModel):
    """Recipe domain model."""
    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    prep_time_min: int
    cook_time_min: int

class RecipeResponse(BaseModel):
    """Output schema for recipe responses."""
    recipes: List[Recipe]
    ingredients: List[str]
    preferences: dict[str, str]
```

### Tool Schemas

```python
class IngredientDetectionOutput(BaseModel):
    """Output from local ingredient detection tool."""
    ingredients: List[str]
    confidence_scores: dict[str, float]
    image_description: str
    filtered_ingredients: bool  # True if any ingredients filtered out
```

**Note:** Spoonacular MCP schemas are defined by the external package, not in our code.

---

## 13. Testing Strategy

### Unit Tests (tests/unit/)

**Scope:** Python code validation, no external calls.

**test_models.py:**
- Pydantic model validation
- Required field enforcement
- Type checking
- Schema edge cases

**test_config.py:**
- Environment variable loading
- Default values
- Validation logic
- .env file precedence

**Example:**
```python
import pytest
from src.models.models import RecipeRequest, RecipeResponse

def test_recipe_request_valid():
    req = RecipeRequest(ingredients=["tomato", "basil"])
    assert req.ingredients == ["tomato", "basil"]
    assert req.diet is None

def test_recipe_request_missing_ingredients():
    with pytest.raises(ValueError):
        RecipeRequest(diet="vegetarian")  # Missing required field
```

**Run:** `pytest tests/unit/ -v`

---

### Integration Tests (tests/integration/)

**Scope:** Agno evals with real API calls and end-to-end flows.

**test_e2e.py:**
- Real image inputs (sample_vegetables.jpg, etc.)
- Real MCP connections (Spoonacular must be available)
- Full request lifecycle
- Conversation flows with session_id
- Ingredient detection accuracy
- Recipe quality validation

**Example:**
```python
from agno.evals import eval_agent
from app import agent
import base64

@eval_agent(agent=agent)
def test_image_to_recipes():
    """Test complete flow: image → ingredients → recipes."""
    # Load test image
    with open("images/sample_vegetables.jpg", "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    # Run agent
    response = agent.run(
        "What recipes can I make?",
        image_base64=image_base64
    )
    
    # Validate
    assert len(response.ingredients) > 0
    assert len(response.recipes) > 0
    assert "tomato" in response.ingredients  # Expected ingredient
    
@eval_agent(agent=agent)
def test_conversation_flow():
    """Test multi-turn conversation with preferences."""
    session_id = "test_session_123"
    
    # Turn 1: Request vegetarian recipes
    r1 = agent.run("Show me vegetarian recipes", session_id=session_id)
    assert "vegetarian" in r1.preferences.get("diet", "").lower()
    
    # Turn 2: Follow-up without repeating preference
    r2 = agent.run("What about Italian cuisine?", session_id=session_id)
    assert "italian" in r2.preferences.get("cuisine", "").lower()
    assert "vegetarian" in r2.preferences.get("diet", "").lower()  # Preserved
```

**Run:** `pytest tests/integration/ -v --log-cli-level=INFO`

**Results:** Stored in AgentOS eval database, queryable via API.

---

## 14. Error Handling & Response Format

### Success Response

AgentOS returns standardized responses:

```json
{
  "session_id": "abc123",
  "run_id": "run_xyz",
  "response": "Based on the tomatoes and basil in your image, here are 3 Italian recipes...",
  "recipes": [
    {
      "title": "Caprese Salad",
      "description": "Fresh tomato and mozzarella...",
      "ingredients": ["tomato", "mozzarella", "basil"],
      "instructions": ["Slice tomatoes...", "Arrange on plate..."],
      "prep_time_min": 10,
      "cook_time_min": 0
    }
  ],
  "ingredients": ["tomato", "basil", "mozzarella"],
  "metadata": {
    "tools_called": ["extract_ingredients", "search_recipes", "get_recipe_information_bulk"],
    "model": "gemini-1.5-flash",
    "response_time_ms": 2341
  }
}
```

### Error Responses

**400 Bad Request:**
- Invalid input format
- Missing required fields
- Invalid base64 encoding
- Invalid image format (not JPEG/PNG)

**413 Payload Too Large:**
- Image exceeds MAX_IMAGE_SIZE_MB (default 5MB)

**422 Unprocessable Entity:**
- Guardrails triggered (off-topic, PII, prompt injection)
- Valid format but business logic failure

**500 Internal Server Error:**
- Unexpected system errors
- Tool call failures (after retries)

**Error Schema:**
```json
{
  "error": "validation_error",
  "message": "Image format must be JPEG or PNG",
  "session_id": "abc123"
}
```

---

## 15. Observability & Tracing

### AgentOS Built-in Tracing

**No external SaaS required** - AgentOS provides tracing automatically.

**What Gets Traced:**
- Agent runs (start, end, duration)
- Tool calls (which tools, parameters, results)
- Model calls (prompts, completions, tokens)
- Errors and exceptions
- Session metadata (preferences, context)

**Trace Metadata:**
```json
{
  "session_id": "abc123",
  "run_id": "run_xyz",
  "tools_called": ["extract_ingredients", "search_recipes"],
  "model": "gemini-1.5-flash",
  "preferences": {"diet": "vegetarian", "cuisine": "italian"},
  "ingredients": ["tomato", "basil"],
  "filtered_ingredients": false,
  "response_time_ms": 2341
}
```

**Access Traces:**
- Via AgentOS REST API endpoints
- Via AGUI web interface (built-in viewer)
- Stored in same database as sessions

**No Configuration Needed:**
- Tracing is always active
- No API keys required
- No external service setup

---

## 16. Makefile Commands

### Command Specifications

```makefile
.PHONY: setup dev run test eval clean

setup:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Creating .env from template..."
	[ -f .env ] || cp .env.example .env
	@echo "✓ Setup complete. Edit .env with your API keys."
	@echo ""
	@echo "Required: GEMINI_API_KEY, SPOONACULAR_API_KEY"

dev:
	@echo "Starting AgentOS in development mode (hot reload)..."
	python app.py

run:
	@echo "Starting AgentOS in production mode..."
	python app.py

test:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

eval:
	@echo "Running Agno integration tests..."
	pytest tests/integration/ -v --log-cli-level=INFO

clean:
	@echo "Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Clean complete"
```

### Usage

- `make setup` - First-time setup (install deps, create .env)
- `make dev` - Start development server with hot-reload
- `make run` - Start production server
- `make test` - Run unit tests (fast, no external calls)
- `make eval` - Run integration tests (requires API keys and MCP)
- `make clean` - Remove cache files

### Development Workflow

1. **Initial Setup:**
   ```bash
   make setup
   # Edit .env with your API keys
   ```

2. **Development:**
   ```bash
   make dev
   # App runs at http://localhost:7777
   # REST API: POST /api/agents/chat
   # Web UI: http://localhost:7777
   ```

3. **Testing:**
   ```bash
   make test  # Unit tests (fast)
   make eval  # Integration tests (requires APIs)
   ```

4. **Access Interfaces:**
   - **REST API:** `curl -X POST http://localhost:7777/api/agents/chat -d '...'`
   - **Web UI:** Open http://localhost:7777 in browser

---

## 17. Implementation Checklist for Coding Agent

### Phase 1: Project Setup
- [ ] Create folder structure (app.py, config.py, models.py, tests/, images/)
- [ ] Initialize .env.example and .gitignore
- [ ] Create requirements.txt with dependencies
- [ ] Set up Makefile with all commands

### Phase 2: Configuration & Models
- [ ] Implement config.py with dotenv loading and validation
- [ ] Define all Pydantic models in models.py
- [ ] Validate model schemas with basic tests

### Phase 3: Local Ingredient Detection Tool
- [ ] Implement @tool decorated function in app.py
- [ ] Call Gemini vision API for ingredient extraction
- [ ] Apply MIN_INGREDIENT_CONFIDENCE filtering
- [ ] Return structured IngredientDetectionOutput
- [ ] Test with sample images

### Phase 4: Agno Agent Configuration
- [ ] Define RecipeRequest and RecipeResponse schemas
- [ ] Configure Gemini model with retry settings
- [ ] Set up database (SqliteDb for dev)
- [ ] Configure memory settings (history, preferences, summaries)
- [ ] Enable context compression
- [ ] Add guardrails (PII detection, prompt injection)
- [ ] Write detailed system instructions

### Phase 5: External MCP Integration
- [ ] Register Spoonacular MCP via MCPTools
- [ ] Test MCP connection (should fail if unreachable)
- [ ] Verify tool availability via system instructions

### Phase 6: AgentOS Application
- [ ] Create AgentOS instance with agent and AGUI
- [ ] Get FastAPI app from agent_os
- [ ] Implement serve() with reload option
- [ ] Test both REST API and Web UI

### Phase 7: Testing
- [ ] Unit tests: test_models.py, test_config.py
- [ ] Integration tests: test_e2e.py with real images
- [ ] Test conversation flows with session_id
- [ ] Verify preference persistence

### Phase 8: Documentation
- [ ] Write comprehensive README.md
- [ ] Document API endpoints and examples
- [ ] Document Web UI usage
- [ ] Verify all Makefile commands work

### Phase 9: Validation
- [ ] Run full test suite (make test && make eval)
- [ ] Test with all sample images
- [ ] Verify conversation memory works
- [ ] Check preference extraction and persistence
- [ ] Validate against PRD success criteria

---

## 18. Critical Implementation Notes

### Critical Do's

✅ **DO** use AgentOS as single entry point (app.py)
✅ **DO** leverage Agno built-in features (memory, retries, guardrails)
✅ **DO** define detailed system instructions (agent behavior)
✅ **DO** use @tool decorator for local ingredient detection
✅ **DO** use MCPTools for external Spoonacular MCP
✅ **DO** validate only external MCPs at startup (not local tools)
✅ **DO** ground responses in tool outputs only
✅ **DO** store image metadata only (NEVER base64)
✅ **DO** use structured schemas everywhere (Pydantic)
✅ **DO** let Agno manage session storage automatically

### Critical Don'ts

❌ **DON'T** create custom FastAPI routes (AgentOS provides them)
❌ **DON'T** write custom orchestration logic (use system instructions)
❌ **DON'T** implement manual memory management (Agno handles it)
❌ **DON'T** store base64 images in memory or database
❌ **DON'T** hardcode secrets or API keys
❌ **DON'T** validate local @tool functions at startup
❌ **DON'T** log raw image bytes (privacy)
❌ **DON'T** create separate CLI scripts (use Web UI or curl)

### Architecture Principles

- **Single entry point**: python app.py
- **Declarative configuration**: System instructions define behavior
- **Built-in infrastructure**: AgentOS provides REST API, Web UI, memory, tracing
- **Automatic tool routing**: Agno decides based on instructions
- **Session persistence**: Automatic via database (SQLite or PostgreSQL)
- **Zero boilerplate**: Focus on business logic (schemas, tools, instructions)

---

## 19. Key Differences from PydanticAI Architecture

### What Changed

| Aspect | PydanticAI Architecture | AgentOS/Agno Architecture |
|--------|------------------------|---------------------------|
| **Entry Point** | main.py (FastAPI) | app.py (AgentOS) |
| **Orchestrator** | orchestrator.py (custom) | Agno Agent (built-in) |
| **REST API** | Custom FastAPI routes | AgentOS built-in endpoints |
| **Web UI** | Separate agentOS_app.py | AGUI (built-in) |
| **Memory** | Manual dict → optional DB | Agno automatic + DB |
| **Tool Integration** | Two external MCPs | @tool (local) + MCPTools (external) |
| **Startup** | 3-4 terminals | 1 terminal |
| **Code Lines** | ~950 lines boilerplate | ~150-200 lines config |
| **Session Storage** | Custom implementation | Built-in (SQLite/PostgreSQL) |
| **Retries** | Manual try/catch | Built-in with exponential backoff |
| **Guardrails** | Custom logic | Built-in pre-hooks |
| **Tracing** | External Langfuse (optional) | AgentOS built-in |

### What Stayed the Same

✓ **Functionality**: All features preserved
✓ **Conversation memory**: Session-based with history
✓ **Preference persistence**: Extracted and remembered
✓ **Ingredient detection**: Vision-based via Gemini
✓ **Recipe search**: Via Spoonacular API
✓ **Guardrails**: Recipe-only domain enforcement
✓ **Error handling**: Same HTTP status codes
✓ **Testing**: Unit tests + integration tests

### Why This Matters

**Before (PydanticAI):**
- ~950 lines of infrastructure code
- Custom memory management
- Custom API routes
- Custom orchestration
- Multiple entry points

**After (AgentOS/Agno):**
- ~150-200 lines of configuration
- Built-in memory (automatic)
- Built-in API (automatic)
- Declarative instructions
- Single entry point

**Result:** Same functionality, 60% less code, zero infrastructure boilerplate.

---

## 20. Success Criteria

A reviewer should be able to:

### Functional Success
- ✅ Run `make setup && make dev` and access both interfaces immediately
- ✅ Send image via REST API and receive structured recipe recommendations
- ✅ Use Web UI at http://localhost:7777 for interactive testing
- ✅ Verify ingredients correctly detected from clear images (>80% accuracy)
- ✅ Test multi-turn conversations with same session_id
- ✅ Confirm preferences persist across conversation turns
- ✅ Verify guardrails prevent off-topic requests

### Technical Success
- ✅ All unit tests pass (`make test`)
- ✅ All integration tests pass (`make eval`)
- ✅ Traces visible with proper metadata
- ✅ Response times reasonable (<10 seconds typical)
- ✅ Code well-structured and documented
- ✅ Zero external dependencies for dev mode (SQLite/LanceDB)
- ✅ Single command startup: `python app.py`

### Code Quality
- ✅ Clear separation: config, models, tools, instructions
- ✅ No custom orchestration logic (system instructions only)
- ✅ No custom API routes (AgentOS built-in)
- ✅ No custom memory code (Agno automatic)
- ✅ Minimal glue code (~150-200 lines total)
- ✅ Easy to understand from documentation

### Extensibility
- ✅ Understand architecture from this document
- ✅ Easily identify where to add new tools (app.py)
- ✅ Clear how to modify agent behavior (system instructions)
- ✅ Understand testing strategy (unit + Agno evals)

---

## 21. Advanced Features (Implemented)

This section documents implemented improvements to demonstrate Agno's full capabilities.

### 21.1 Advanced Memory Management

**What's Implemented:**
- **MemoryManager** automatically captures user preferences
- Configurable memory window via **MAX_HISTORY** (default: 3 conversation turns)
- **Session Summaries** auto-generated for long conversations (ENABLE_SESSION_SUMMARIES)
- **Context Compression** after N tool calls (COMPRESS_TOOL_RESULTS)

**Preferences Captured (Persistent Across Sessions):**
- Diet: vegetarian, vegan, gluten-free, dairy-free, paleo, keto, etc.
- Allergies: shellfish, peanuts, tree nuts, soy, milk, eggs, fish, wheat, sesame, etc.
- Cuisines: italian, asian, mexican, indian, mediterranean, french, japanese, thai, etc.
- Cooking time preferences: quick meals, slow cooking, etc.

**Preferences NOT Captured (Ephemeral):**
- Specific meal requests ("I want pasta for dinner")
- Temporary cravings ("something spicy today")
- One-time requests ("feed 10 people")

**Configuration (in config.py):**
```python
# Number of historical conversation turns included in context
MAX_HISTORY = 3

# Enable automatic session summarization for long conversations
ENABLE_SESSION_SUMMARIES = True

# Enable context compression after tool calls
COMPRESS_TOOL_RESULTS = True
COMPRESS_TOOL_RESULTS_LIMIT = 3  # Compress after 3+ tool calls
```

**Implementation (in app.py):**
```python
memory_manager = MemoryManager(
    model=model,
    memory_capture_instructions="""
    Capture user preferences: diet, allergies, cuisines.
    Exclude: ephemeral requests, meal-specific preferences.
    """
)

agent = Agent(
    memory_manager=memory_manager,
    enable_user_memories=True,
    enable_session_summaries=config.enable_session_summaries,
    num_history_runs=config.max_history,
    compress_tool_results=config.compress_tool_results,
    compress_tool_results_limit=config.compress_tool_results_limit,
    ...
)
```

### 21.2 Automatic Retry with Exponential Backoff

**Configured at Two Levels:**

**Level 1: Model Retries (Gemini API calls)**
```python
model = Gemini(
    id=config.gemini_model,
    retries=2,                    # Retry on failures
    delay_between_retries=1,      # 1 second initial delay
    exponential_backoff=True      # 1s → 2s → 4s
)
```

**Level 2: Pre-Hook Retries (Ingredient Detection)**
In `ingredients.py`, the `_extract_with_retries()` function:
- Retries up to 3 times on transient failures
- Exponential backoff: 1s, 2s, 4s
- Logs all retry attempts for debugging
- Fails gracefully (returns empty ingredients) instead of crashing

### 21.3 Structured Outputs Validation

All inputs and outputs validated via Pydantic:

**Request Validation:**
```python
agent = Agent(
    input_schema=RecipeRequest,
    ...
)
```

**Response Validation:**
```python
agent = Agent(
    output_schema=RecipeResponse,
    ...
)
```

**OpenAPI Documentation (Auto-Generated):**
- Endpoint: `http://localhost:7777/docs`
- Provides interactive API testing
- Automatic from Pydantic schemas
- No custom code needed (AgentOS handles it)

### 21.4 Built-In Guardrails

**Safety Features:**
- **PIIDetectionGuardrail**: Masks sensitive personal information (emails, phone numbers, SSN, credit cards)
- **PromptInjectionGuardrail**: Detects and blocks prompt injection attacks
- System instructions keep agent focused on recipes only

**Configuration (in app.py):**
```python
agent = Agent(
    pre_hooks=[
        extract_ingredients_pre_hook,        # Extract from images first
        PIIDetectionGuardrail(mask_pii=True),  # Mask sensitive info
        PromptInjectionGuardrail()             # Block attacks
    ],
    ...
)
```

### 21.5 What's NOT Implemented (and Why)

**Semantic Memory (PI-8):**
- NOT implemented (documented as future-only)
- Reason: Expensive LLM calls for every interaction
- Alternative: Keep simple MAX_HISTORY approach (more efficient)

**Streaming Responses (PI-2):**
- NOT needed (built-in to AgentOS)
- AgentOS handles Server-Sent Events (SSE) automatically
- No custom implementation required

**Human-in-Loop Workflows (PI-6):**
- NOT implemented (not needed for recipe service)
- Recipes don't require human approval
- Out of scope for initial MVP

---

## 22. Final Notes for Coding Agent

This system demonstrates **production-quality GenAI engineering** using AgentOS:

**Core Strengths:**
- Single entry point with complete infrastructure
- Built-in memory, retries, guardrails, compression
- Declarative configuration over imperative code
- Zero external dependencies for development
- Professional testing strategy (unit + integration)
- Clear separation of concerns

**Implementation Focus:**
- Write schemas (Pydantic models)
- Implement local tools (@tool functions)
- Write system instructions (agent behavior)
- Configure Agno Agent (model, database, memory, guardrails)
- Set up AgentOS (agents + interfaces)

**What AgentOS Handles:**
- REST API endpoints (automatic)
- Web UI interface (AGUI)
- Session management (per session_id)
- Memory persistence (SQLite/PostgreSQL)
- Tool lifecycle (MCP connections)
- Error handling and logging
- Tracing and evaluations

**When in doubt:**
1. Refer to PRD requirements
2. Prefer simplicity (let AgentOS handle infrastructure)
3. Use system instructions (not code) for behavior
4. Trust Agno's automatic features (memory, retries, guardrails)
5. Test incrementally (unit tests, then integration)

**Success = Production-ready service in ~150-200 lines of business logic.**
