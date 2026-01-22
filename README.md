# Image-Based Recipe Recommendation Service

A production-quality GenAI system that transforms ingredient images into structured recipe recommendations using modern orchestration patterns (AgentOS, Agno Agent, MCP).

## Overview

This service demonstrates best practices in system design by leveraging **AgentOS** as the complete runtime backbone, **Agno Agent** as the intelligent orchestrator, and **Gemini Vision API** for ingredient detection from images.

### Key Capabilities

- 📸 **Image-Based Ingredient Detection** - Upload ingredient photos, automatically extract ingredients using Gemini vision API
- 🍳 **Recipe Recommendations** - Get personalized recipes based on detected ingredients and preferences
- 💬 **Conversational Memory** - Multi-turn conversations with automatic preference tracking (dietary restrictions, cuisines, meal types)
- 🎯 **Domain-Focused** - Specialized for recipes only, with guardrails preventing off-topic requests
- 🔄 **Session Management** - Persistent conversation history and user preferences across sessions
- 📊 **Structured Output** - All responses validated with Pydantic schemas

## Features

### Core Agent Features

- ✅ **Exponential Backoff Retries** (3 attempts, 2s→4s→8s delays) - Handles transient failures and rate limits
- ✅ **Structured Output** - Pydantic schema validation for type-safe responses
- ✅ **Multi-Model Support** - Configurable LLM selection (Gemini Flash/Pro, Claude, GPT)
- ✅ **Automatic Memory** - User preferences and conversation history (with compression)
- ✅ **Session Persistence** - SQLite/PostgreSQL support for production deployments
- ✅ **Tool Integration** - MCP protocol + internal tools with pre/post hooks and guardrails

### Observability & Quality

- ✅ **Distributed Tracing** - AgentOS built-in OpenTelemetry integration for execution visibility
- ✅ **Structured Logging** - Python logging with debug/info/warning levels (no sensitive data)
- ✅ **Unit Tests** - 150+ tests for models, config, ingredients, MCP, tracing
- ✅ **Integration Tests** - E2E evaluation tests with Agno Evals Framework (accuracy, reliability, performance)
- ✅ **REST API Tests** - 13 endpoint tests covering session management, file uploads, error handling

### Data & Knowledge

- ✅ **Knowledge Graph** - LanceDB vector store with SentenceTransformer embeddings (no API cost)
- ✅ **Semantic Search** - Troubleshooting findings stored and searchable for agent learning
- ✅ **Error Tracking** - API errors (402 quota, 429 rate limit) documented for diagnostics

### System Design

- ✅ **MCP Tools** - Spoonacular recipe API with custom retry logic and connection validation
- ✅ **Internal Tools** - Ingredient detection tool (image→ingredients with confidence scores)
- ✅ **Pre/Post Hooks** - Image processing, guardrails, metadata injection, troubleshooting tracking
- ✅ **Templated Prompts** - Configurable system instructions with dynamic parameters (MAX_RECIPES, MIN_CONFIDENCE, etc)
- ✅ **AgentOS Integration** - REST API + Web UI + chat interface provided out-of-the-box

### Architecture Overview

```mermaid
graph TD
    A["User Request<br/>(Image or Text)"] --> B["Pre-Hook<br/>Ingredient Detection"]
    B --> C["Agno Agent<br/>Orchestrator"]
    C --> D["Spoonacular MCP<br/>Recipe Search"]
    D --> E["Recipe Response<br/>with Preferences"]
    
    C -.->|Session Memory| F["SQLite/PostgreSQL<br/>Database"]
    F -.->|Load History| C
    
    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E fill:#e1f5ff
    style F fill:#f5f5f5
```

## Quick Start

### Prerequisites
- Python 3.8+
- API Keys:
  - [Google Gemini API Key](https://ai.google.dev/docs) (for vision/ingredient detection)
  - [Spoonacular API Key](https://spoonacular.com/food-api) (for recipe search)

### Setup

```bash
# 1. Clone and initialize
git clone <repo-url>
cd recipe-agent

# 2. Setup dependencies and environment
make setup

# 3. Edit .env with your API keys
# Required:
#   GEMINI_API_KEY=your_key_here
#   SPOONACULAR_API_KEY=your_key_here
nano .env

# 4. Start the application
make dev
```

The service will start at:
- **Backend API**: `http://localhost:7777`
- **OpenAPI Docs**: `http://localhost:7777/docs`
- **Agno OS Platform**: [https://os.agno.com](https://os.agno.com) (recommended UI - connect local agent)

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Runtime** | AgentOS | Complete application backend (REST API, orchestration, tracing) |
| **Orchestrator** | Agno Agent | Stateful agent with memory, retries, and tool routing |
| **Vision API** | Gemini (3-flash-preview) | Ingredient detection from images |
| **Recipe Search** | Spoonacular MCP | 50K+ verified recipes via external service |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Session storage and memory |
| **Validation** | Pydantic v2 | Input/output schema validation |
| **Testing** | pytest + Agno Evals | Unit, integration, and evaluation testing |

## Setup Instructions

### 1. Install Dependencies

```bash
make setup
```

This will:
- Install all Python dependencies from `requirements.txt`
- Create `.env` file from `.env.example` (if not already present)
- Display instructions for adding API keys

### 2. Configure Environment

Edit `.env` and add your API keys:

```bash
# Required - Get from Google Cloud Console
GEMINI_API_KEY=your_gemini_key_here

# Required - Get from spoonacular.com/food-api or rapidapi.com
SPOONACULAR_API_KEY=your_spoonacular_key_here

# Optional - Defaults shown
# Default: gemini-3-flash-preview (fast, cost-effective)
# For best results: gemini-3-pro-preview
GEMINI_MODEL=gemini-3-flash-preview
PORT=7777
MAX_HISTORY=3
MAX_RECIPES=3
MAX_IMAGE_SIZE_MB=5
MIN_INGREDIENT_CONFIDENCE=0.7
IMAGE_DETECTION_MODE=pre-hook
LOG_LEVEL=INFO
OUTPUT_FORMAT=json
# DATABASE_URL=postgresql://user:pass@localhost:5432/recipe_service
```

#### Getting Spoonacular API Key

**Option 1: Direct from Spoonacular (Recommended)**

1. Visit [spoonacular.com/food-api](https://spoonacular.com/food-api)
2. Click **"Get API Key"** button
3. Sign up or log in with email
4. Your API key appears on the dashboard
5. Copy to `.env` as `SPOONACULAR_API_KEY`

**Option 2: Via RapidAPI**

1. Visit [RapidAPI Spoonacular Recipe API](https://rapidapi.com/spoonacular/api/recipe-food-nutrition/pricing)
2. Click **"Subscribe to Test"** (free plan available)
3. Copy API key from RapidAPI dashboard
4. Use with `.env`: `SPOONACULAR_API_KEY=your_key_here`

#### Understanding Spoonacular Quotas

**Free Plan:**
- **API Calls**: 100/day
- **Cost**: $0/month
- **Use Case**: Development and testing
- **Throttle**: 1 request/second

**Quota Status:**
- Check remaining quota in `.env` file or dashboard
- When exceeded: API returns `402 Payment Required` error
- Daily quota resets at **00:00 UTC**

**Tips to Minimize Usage:**
- Use stateless mode (`S=1`) for testing: doesn't persist or re-query
- Cache recipe results in your database
- Batch multiple ingredient searches into one recipe search
- Use `get_recipe_information_bulk` for multiple recipes at once (more efficient)

**Current Status:**
If you see `402 Payment Required` errors in responses:
```
"API request failed: 402 Payment Required"
```
This means your daily quota is exhausted. Options:
1. Upgrade to a paid plan
2. Wait until daily reset (UTC midnight)
3. Use test mode with different Spoonacular account

### 3. Start Development Server

```bash
make dev
```

The application will start at:
- **Backend**: Python/AgentOS server on `http://localhost:7777`
- **OpenAPI Docs**: `http://localhost:7777/docs`
- **Agno OS UI**: [https://os.agno.com](https://os.agno.com) (connect local agent for web UI, traces, evaluations)

## Using the Web UI with Agno OS Platform

### Quick Start with Agno OS

1. **Create Free Account**: Visit [os.agno.com](https://os.agno.com) and sign up (free tier available)
2. **Start Backend**: Run `make dev` (starts your local agent on http://localhost:7777)
3. **Connect Agent**: In Agno OS platform → Click team dropdown → "Add new OS" → Select "Local" → Enter endpoint `http://localhost:7777`
4. **Chat in Platform**: UI automatically adapts to your agent's input schema
5. **View Traces**: Agno OS platform shows execution traces, tool calls, and reasoning

### Why Agno OS Platform?

- **Schema-Aware UI**: Forms and inputs automatically adapt to your agent's request schema
- **Execution Traces**: See every step of ingredient detection and recipe search
- **Session Persistence**: Multi-turn conversations with automatic memory management
- **Evaluations**: Built-in framework for testing agent quality
- **No Hosting Needed**: Connect local agents instantly; data stays on your machine

### Key Features in Agno OS

| Feature | Description |
|---------|-------------|
| **Dynamic UI Forms** | Input forms automatically generated from your agent's schema |
| **Execution Traces** | Full visibility: agent thinking, tool calls, LLM reasoning |
| **Session History** | Persistent multi-turn conversations |
| **Image Support** | Upload images directly (base64 conversion handled) |
| **Tool Inspection** | See which MCP tools were called and their outputs |
| **Performance Metrics** | Response times, token usage, execution breakdown |

### Uploading Images for Ingredient Detection

1. **Use Agno OS Upload Widget** - Click image upload in chat input
2. **Select Ingredient Photos** - Single or multiple images
3. **Optional Message** - Add notes like "Make it vegetarian" or just send images
4. **Auto-Extraction** - Gemini Vision API detects ingredients automatically
5. **View Results** - Recipes with full details returned in Agno UI

**Image Requirements:**
- **Max Size**: 5MB per image
- **Formats**: JPEG, PNG, WebP, GIF
- **Best Practice**: Clear, well-lit photos of actual food items

## Development Workflow

### Start Server

```bash
make dev     # Development mode (debug log level, JSON output format)
make debug   # Full debug mode (log level + agent debug + debug level 2, JSON output)
make run     # Production mode (markdown output format for UI rendering)
make stop    # Stop running server
```

**Output Formats:**
- `make dev` and `make debug`: **JSON** - Full RecipeResponse structure (useful for testing/debugging)
- `make run`: **Markdown** - Extracted response field only (optimized for Agno Agent UI rendering)

**Access Points:**
- **Agno OS Platform**: [https://os.agno.com](https://os.agno.com) → Connect local agent → View UI, traces, and evaluations
- **REST API**: `http://localhost:7777/agents/recipe-recommendation-agent/runs` (AgentOS API)
- **API Documentation**: `http://localhost:7777/docs` (Swagger UI)

### Run Ad Hoc Queries

Execute single queries without starting the full server:

```bash
make query Q="What can I make with chicken and rice?"
make query Q="Show me vegetarian recipes"
```

The query command initializes the agent and executes one-off requests from the CLI. Useful for testing or integration with shell scripts.

### Debug Mode

**Development Server:**
- `make dev` - Starts with debug log level (LOG_LEVEL=DEBUG)
- `make debug` - Full debug mode with agent debugging enabled:
  - `LOG_LEVEL=DEBUG` - Structured logging at debug level
  - `DEBUG_MODE=1` - Enables Agno agent debug mode for detailed execution traces
  - `DEBUG_LEVEL=2` - Maximum verbosity for agent reasoning and tool calls

**Debug output shows:**
- 📞 **Tool Calls** - Which MCP tools were called and their arguments
- 💬 **LLM Communication** - Complete system prompt, user input, and model output
- ⏱️ **Performance Metrics** - Token counts, execution time, tokens/second throughput
- 🔄 **Session Management** - Memory operations and preference tracking
- 🎯 **Pre-Hooks** - Ingredient detection from images

### Run Tests

```bash
make test    # Unit tests (fast, isolated)
make eval    # Integration tests (requires API keys)
```

### Clean Cache

```bash
make clean   # Remove __pycache__, .pyc, pytest cache
```

## Usage Examples

### Web UI via Agno OS Platform (Recommended)

1. Start backend: `make dev`
2. Go to [https://os.agno.com](https://os.agno.com) (free account available)
3. Add new OS: Team dropdown → "Add new OS" → Local → `http://localhost:7777`
4. Chat: UI auto-adapts to agent schema, view traces and executions

### REST API (Programmatic)

#### Text Query

```bash
curl -X POST http://localhost:7777/agents/recipe-recommendation-agent/runs \
  -d 'message={"message": "I have tomatoes and basil", "session_id": "user-123"}'
```

#### Image Upload (Base64)

```bash
curl -X POST http://localhost:7777/agents/recipe-recommendation-agent/runs \
  -d "message={\"images\": \"data:image/jpeg;base64,...\"}"
```

#### Multi-Turn Conversation (Preferences Persisted)

```bash
# Turn 1: Express preference
curl -X POST http://localhost:7777/agents/recipe-recommendation-agent/runs \
  -d "message={\"message\": \"I am vegetarian\", \"session_id\": \"user-123\"}"

# Turn 2: Agent remembers vegetarian preference
curl -X POST http://localhost:7777/agents/recipe-recommendation-agent/runs \
  -d "message={\"message\": \"I have potatoes and garlic\", \"session_id\": \"user-123\"}"
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | string | **required** | Google Gemini API key (vision model) |
| `SPOONACULAR_API_KEY` | string | **required** | Spoonacular recipe API key |
| `GEMINI_MODEL` | string | `gemini-3-flash-preview` | Vision model (fast). Options: `gemini-3-flash-preview`, `gemini-3-pro-preview` |
| `PORT` | int | `7777` | Server port |
| `MAX_HISTORY` | int | `3` | Conversation turns to keep in memory |
| `MAX_RECIPES` | int | `3` | Maximum recipes to return per request |
| `MAX_IMAGE_SIZE_MB` | int | `5` | Maximum image upload size |
| `MIN_INGREDIENT_CONFIDENCE` | float | `0.7` | Confidence threshold for detected ingredients (0.0-1.0) |
| `IMAGE_DETECTION_MODE` | string | `pre-hook` | Detection mode: `pre-hook` (fast) or `tool` (agent-controlled) |
| `TOOL_CALL_LIMIT` | int | `6` | Maximum tool calls per agent request (prevents excessive API usage) |
| `OUTPUT_FORMAT` | string | `json` | Response format: `json` or `markdown` |
| `LOG_LEVEL` | string | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `DATABASE_URL` | string | *optional* | PostgreSQL connection (SQLite default) |
| `ENABLE_TRACING` | bool | `true` | Enable distributed tracing |
| `TRACING_DB_TYPE` | string | `sqlite` | Tracing database type: `sqlite` or `postgres` |
| `TRACING_DB_FILE` | string | `agno_traces.db` | Path for SQLite tracing database |

### Observability & Tracing

Built-in tracing with OpenTelemetry. View traces in Agno OS Platform:

```bash
# Start backend
make dev

# Connect to https://os.agno.com
# 1. Create account (free tier available)
# 2. Add new OS → Local → http://localhost:7777
# 3. View traces in /traces tab
```

**Disable Tracing (if needed):**
```bash
ENABLE_TRACING=false
```

### Database Configuration

**Development (Default):**
SQLite file: `agno.db` (auto-created)

**Production (PostgreSQL):**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/recipe_service
```

## Architecture

### Data Flow

1. **Request** → User sends message and/or image
2. **Pre-Hook** → Images processed through Gemini vision API to extract ingredients
3. **Agent** → Agno Agent routes to recipe tools with extracted ingredients + preferences
4. **Recipe Search** → Spoonacular MCP called to find matching recipes
5. **Response** → Agent synthesizes human-friendly response with recipe details

### Session Management

- Each conversation has a unique `session_id`
- Agent automatically maintains chat history (last N turns, configurable)
- User preferences extracted and persisted per session
- Preferences applied to subsequent requests without re-stating
- Sessions survive application restarts (stored in database)

### Key Design Decisions

**1. Pre-Hook Pattern** (images processed BEFORE agent executes)
- Eliminates extra LLM round-trip
- Keeps ingredients as text (not raw bytes) in chat history
- Faster responses overall
- Configurable via `IMAGE_DETECTION_MODE` environment variable

**Flexible Ingredient Detection (Pre-Hook vs. Tool):**
- `IMAGE_DETECTION_MODE=pre-hook` (default): Fast, processes before agent, no extra LLM call
- `IMAGE_DETECTION_MODE=tool`: Agent control, visible tool call, agent decides when/if to call
- Same core detection code used for both modes
- Switch modes via environment variable only (no code changes needed)

**3. Two-Step Recipe Process**
- Search recipes (ingredients + filters) via Spoonacular MCP
- Get full recipe details (prevents hallucination)
- All responses grounded in actual data

**4. System Instructions Over Code**
- Agent behavior defined declaratively (not hard-coded)
- Domain boundaries, preference extraction in prompts.py
- Easy to modify behavior without code changes

### Module Responsibilities

- **app.py**: Orchestration (minimal ~50 lines)
- **agent.py**: Agent initialization (factory pattern)
- **prompts.py**: Behavior definition (system instructions)
- **hooks.py**: Pre-hook configuration (factory pattern)
- **config.py**: Environment and validation
- **logger.py**: Structured logging
- **models.py**: Data validation (Pydantic)
- **ingredients.py**: Image processing (core functions)
- **mcp_tools/spoonacular.py**: MCP initialization

### Database & Storage

**Development (Default):**
- SQLite + LanceDB (file-based, zero setup)
- Database file: agno.db

**Production (Optional):**
- PostgreSQL + pgvector (set DATABASE_URL)

### Knowledge Base

Agent maintains a searchable knowledge base (LanceDB) of recipe insights and troubleshooting findings:

**Automatically Stored:**
- Failed recipe searches (queries, failure reasons)
- API errors and retries
- User preferences and patterns
- Recipe combinations that work/don't work

**Used For:**
- Avoiding repeated failed searches
- Context for future similar requests
- Improved recommendations over time
- Debugging search patterns

**Search Enabled:** Agent can search knowledge base for similar past issues before attempting new searches (configurable via `search_knowledge=True` in agent config).



## API Reference

### POST /api/agents/chat

Send a message and/or image to get recipe recommendations.

**Request Schema (ChatMessage):**
```json
{
  "message": "string (optional) - Natural language query like 'I have chicken and rice' (1-2000 chars, optional if images provided)",
  "images": "string or string[] (optional) - Image URL(s) or base64-encoded image(s) (optional if message provided)"
}
```

**Notes:**
- Either `message` or `images` must be provided
- If only images provided, defaults to: "What can I cook with these ingredients?"
- Images can be URLs (http://, https://) or base64-encoded strings
- Max 10 images per request
- Automatically extracts ingredients from images using Gemini vision API

**Response Schema (RecipeResponse):**
```json
{
  "response": "string - LLM-generated conversational response",
  "recipes": [
    {
      "title": "string - Recipe name",
      "description": "string (optional) - Brief description",
      "ingredients": ["string"] - Ingredient list with quantities",
      "instructions": ["string"] - Step-by-step cooking instructions",
      "prep_time_min": integer - Preparation time in minutes (0-1440)",
      "cook_time_min": integer - Cooking time in minutes (0-1440)",
      "source_url": "string (optional) - URL to original recipe"
    }
  ],
  "ingredients": ["string (optional)"] - Detected/provided ingredients",
  "preferences": "object (optional) - User preferences (diet, cuisine, meal_type, intolerances)",
  "session_id": "string (optional) - Session identifier for continuity",
  "run_id": "string (optional) - Unique ID for this execution",
  "execution_time_ms": integer - Total execution time in milliseconds
}
```

**Error Responses:**
- `400 Bad Request` - Missing both message and images, or malformed JSON
- `413 Payload Too Large` - Image exceeds MAX_IMAGE_SIZE_MB
- `422 Unprocessable Entity` - Off-topic request (guardrail enforced)
- `500 Internal Server Error` - Unexpected system error

## Testing

### Unit Tests (Fast, Isolated)

```bash
make test
```

Tests:
- Configuration loading and validation
- Pydantic model validation
- Schema serialization/deserialization

### Integration Evals (Agno Evals Framework)

```bash
# Terminal 1: Start AgentOS
make dev

# Terminal 2: Run evaluations
make eval
```

Uses **Agno evals framework** (AgentOS built-in evaluation system) for multi-dimensional testing:

- **AccuracyEval**: Ingredient detection accuracy using LLM-as-judge
- **AgentAsJudgeEval**: Recipe quality, preference persistence, guardrails, session isolation
- **ReliabilityEval**: Correct tool sequence (search_recipes → get_recipe_information_bulk)
- **PerformanceEval**: Response time under 5 seconds

**Coverage:** 8 comprehensive eval tests covering all dimensions.

**Viewing Results in UI:**
1. Keep AgentOS running (`make dev`)
2. Run evaluations (`make eval`)
3. Connect [os.agno.com](https://os.agno.com) to `http://localhost:7777`
4. View eval results in the "Evaluations" tab
5. Results are persisted in `tmp/recipe_agent_sessions.db` (shared with agent)

**Note:** Requires valid API keys (GEMINI_API_KEY, SPOONACULAR_API_KEY) and internet connection.

### REST API Integration Tests

```bash
# Start app in one terminal
make dev

# In another terminal, run REST API tests
make int-tests
```

Tests REST API endpoints directly using httpx client. Validates:

- **Successful requests**: HTTP 200 with proper response schema
- **Session management**: Preference persistence across requests, session isolation
- **Image handling**: Base64 image upload and ingredient extraction
- **Error handling**: Missing fields (400), invalid JSON (400), off-topic (422), oversized image (413)
- **Response validation**: RecipeResponse schema compliance
- **Rapid requests**: Handles sequential requests without resource exhaustion

**Coverage:** 13 test functions covering all HTTP status codes and edge cases.

**Note:** Requires running app (`make dev` in separate terminal). Tests connect to `http://localhost:7777`.

## Troubleshooting

### "Spoonacular MCP unreachable" on startup

**Problem:** Application fails to start with MCP connection error.

**Solution:**
1. Verify internet connection
2. Check SPOONACULAR_API_KEY is valid
3. Test API key: `curl "https://api.spoonacular.com/recipes/info?ids=1&apiKey=YOUR_KEY"`
4. If valid, MCP may be temporarily unavailable; try again

### "API key invalid" errors during requests

**Problem:** Requests fail with authentication errors.

**Solution:**
1. Verify `.env` file has correct keys (no extra spaces)
2. Regenerate API keys from their respective consoles
3. Check key hasn't expired or been revoked
4. Restart application after updating keys

### "Image too large" error

**Problem:** Image upload fails with 413 error.

**Solution:**
1. Check image size: `ls -lh path/to/image.jpg`
2. Resize if needed: `convert image.jpg -resize 1024x1024 image-resized.jpg`
3. Adjust threshold if needed: Set `MAX_IMAGE_SIZE_MB=10` in `.env`
4. Restart application

### "No ingredients detected" despite uploading image

**Problem:** Image uploaded but no ingredients extracted.

**Solution:**
1. Verify image shows clear, recognizable food items
2. Try increasing confidence threshold: Lower `MIN_INGREDIENT_CONFIDENCE` in `.env`
3. Try different image format (JPEG vs PNG)
4. Check image is not too dark, blurry, or obscured

### Port already in use

**Problem:** "Address already in use" error on startup.

**Solution:**
1. Change port: `PORT=8888 make dev`
2. Or kill process using port: `lsof -ti:7777 | xargs kill -9`

### Database errors

**Problem:** SQLite or PostgreSQL connection errors.

**Solution:**
1. For SQLite: Delete `agno.db` and restart (fresh database)
2. For PostgreSQL: Verify DATABASE_URL is correct
3. Check database server is running
4. Ensure database user has create/read/write permissions

## Project Structure

```
recipe-agent/
├── app.py                 # AgentOS entry point (~50 lines, minimal orchestration)
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
├── Makefile               # Development commands (setup, dev, test, etc.)
├── README.md              # This file
│
├── src/                   # Application source code (organized by responsibility)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py      # Environment configuration and validation
│   │   └── logger.py      # Structured logging infrastructure
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py      # Pydantic schemas (RecipeRequest, RecipeResponse)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   └── agent.py       # Agent factory function (initialize_recipe_agent)
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── prompts.py     # System instructions (SYSTEM_INSTRUCTIONS constant)
│   │
│   ├── hooks/
│   │   ├── __init__.py
│   │   └── hooks.py       # Pre-hooks factory (get_pre_hooks)
│   │
│   └── mcp_tools/
│       ├── __init__.py
│       ├── ingredients.py # Ingredient detection (core functions + pre-hook/tool)
│       └── spoonacular.py # SpoonacularMCP class (MCP initialization with retry logic)
│
├── tests/
│   ├── unit/              # Unit tests (isolated, no external APIs)
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_logger.py
│   │   ├── test_ingredients.py
│   │   ├── test_mcp.py
│   │   └── test_app.py
│   └── integration/       # Integration tests (evals + REST API)
│       ├── conftest.py     # Pytest fixtures and configuration
│       ├── test_eval.py    # Agno evals framework (8 comprehensive tests)
│       └── test_integration.py # REST API endpoint tests (13 tests)
│
├── images/                # Sample test images
│   ├── sample_vegetables.jpg
│   ├── sample_fruits.jpg
│   └── sample_pantry.jpg
│
└── .docs/                 # Documentation
    ├── PRD.md             # Product requirements
    ├── DESIGN.md          # Technical design (factory pattern, architecture)
    └── IMPLEMENTATION_PLAN.md  # Task breakdown
```

## Development Guidelines

### Code Quality

- **Type Hints**: All functions have type annotations
- **Docstrings**: All public functions documented
- **Error Handling**: Graceful error messages, no stack traces in API responses
- **Logging**: Structured logging with no sensitive data (keys, images)
- **Testing**: Unit tests for all new code, integration tests for flows

### Adding New Features

**To add a new recipe tool:**
1. Create MCPTools instance with new command
2. Update system instructions to explain when to use it
3. Add integration test for new tool
4. Update README with new capability

**To modify agent behavior:**
1. Edit system instructions in `app.py`
2. No code logic needed (instructions guide behavior)
3. Test with different user inputs
4. Update README if behavior changes significantly

**To add new preferences:**
1. Update RecipeRequest model in `models.py`
2. Update system instructions to extract new preference
3. Preference automatically tracked per session
4. Add test case for new preference

## References

- [PRD.md](.docs/PRD.md) - Complete functional requirements
- [DESIGN.md](.docs/DESIGN.md) - Technical architecture and decisions
- [IMPLEMENTATION_PLAN.md](.docs/IMPLEMENTATION_PLAN.md) - Task breakdown

## License

This is a project demonstrating production-quality GenAI system design.

---

**Questions or Issues?** See [Troubleshooting](#troubleshooting) section above.
