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
- **Web UI (AGUI)**: http://localhost:7777
- **REST API**: http://localhost:7777/api/agents/chat
- **OpenAPI Docs**: http://localhost:7777/docs

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Runtime** | AgentOS | Complete application backend (REST API, Web UI, orchestration) |
| **Orchestrator** | Agno Agent | Stateful agent with memory, retries, and tool routing |
| **Vision API** | Gemini 1.5 Flash | Ingredient detection from images |
| **Recipe Search** | Spoonacular MCP | 50K+ verified recipes via external service |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Session storage and memory |
| **Validation** | Pydantic v2 | Input/output schema validation |
| **Testing** | pytest | Unit and integration testing |

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
MAX_IMAGE_SIZE_MB=5
MIN_INGREDIENT_CONFIDENCE=0.7
IMAGE_DETECTION_MODE=pre-hook
LOG_LEVEL=INFO
LOG_TYPE=text
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

The application will start with full logging and hot-reload support. This starts both:
- **Backend**: Python/AgentOS server on port 7777
- **Frontend**: Next.js Agent UI on port 3000

## Using the Web UI

### Getting Started

1. Open http://localhost:3000 in your browser
2. The Agent UI will automatically connect to http://localhost:7777 (default backend)
3. Add optional auth token if needed (usually not required for local development)
4. Select an agent from the dropdown
5. Start chatting!

### Uploading Images for Ingredient Detection

The Agent UI supports multiple image uploads for automatic ingredient detection:

#### Step-by-Step

1. **Click the Image Upload Button** (📎 plus icon) in the chat input area
2. **Select One or More Images** - You can select multiple ingredient photos at once
3. **View Image Thumbnails** - Selected images display as previews before sending
4. **Add a Message (Optional)**:
   - If you upload images **without typing a message**, the UI automatically sends: *"Show me recipes based on these ingredients"*
   - Or **type your own prompt** like: *"Make something vegetarian with these"* or *"I'm allergic to nuts, what can I make?"*
5. **Click Send** - Images are converted to base64 and sent with your message to the agent

#### Image Upload Specifications

- **Max File Size**: 5MB per image (automatically validated on the client)
- **Max Images per Request**: Unlimited (but larger batches may take longer to process)
- **Supported Formats**: JPEG, PNG, WebP, GIF, and other common image formats
- **Best Results**: Clear, well-lit photos of actual food items
- **Automatic Detection**: Agent uses Gemini Vision API to identify ingredients

#### Example Workflow

1. **Take or Select a Photo** of your ingredients (e.g., tomatoes, basil, mozzarella)
2. **Click Image Button** → select the photo from your device
3. **Photo Thumbnail Appears** → review before sending
4. **Click Send** (no message needed) → UI automatically sends default message
5. **Agent Processes**:
   - Detects ingredients: tomatoes, basil, mozzarella
   - Finds matching recipes: Caprese Salad, Margherita Pizza, Tomato Basil Soup
   - Returns recipes with full details (ingredients, instructions, cooking time)

### Web UI Features

- **Multi-Turn Conversations**: Talk to your agent and it remembers previous messages
- **Session History**: Your chat history is automatically saved and can be reopened later
- **Real-Time Streaming**: See responses as they're generated (character by character)
- **Tool Calls**: View which tools the agent called (recipe search, ingredient detection)
- **Reasoning Steps**: See the agent's thinking process (when available)
- **Preferences Learning**: Agent learns and remembers your dietary preferences, cuisine preferences, and restrictions across messages in a session
- **Image Thumbnails**: Preview uploaded images before sending

## Development Workflow

### Start Server

```bash
make dev     # Development mode with output (Backend + Frontend)
make run     # Production mode
make stop    # Stop running server
```

**Access Points:**
- **Interactive Web UI**: http://localhost:3000 (Modern Agent UI with image upload)
- **REST API**: http://localhost:7777/api/agents/chat
- **API Documentation**: http://localhost:7777/docs (Swagger UI)

### Run Ad Hoc Queries

Execute single queries without starting the full server:

```bash
make query Q="What can I make with chicken and rice?"
make query Q="Show me vegetarian recipes"
```

The query command:
- Initializes the agent (including MCP tools)
- Executes the query
- Prints the response
- Exits cleanly (no lingering processes)

Useful for:
- Testing agent behavior without the server UI
- Quick recipe lookups from the command line
- Debugging without API overhead
- Integration with shell scripts and automation

### Debug Mode

Enable debug output to see internal agent execution details including tool calls, LLM input/output, and performance metrics:

```bash
# Enable debug for web server
make dev DEBUG=1
make run DEBUG=1

# Enable debug for query
make query Q="What can I make with chicken?" DEBUG=1
make query Q="What can I make with chicken?" S=1 DEBUG=1
```

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

### Web UI (Interactive)

1. Navigate to http://localhost:7777
2. Upload an ingredient image or type ingredients
3. Set preferences (dietary restrictions, cuisines)
4. View recipe recommendations with full details

### REST API (Programmatic)

#### Example 1: Text Ingredients → Recipes

```bash
curl -X POST http://localhost:7777/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have tomatoes, basil, and mozzarella. Show me recipes.",
    "session_id": "user-123"
  }'
```

**Response:**
```json
{
  "session_id": "user-123",
  "run_id": "run-456",
  "response": "Great! Here are some Italian recipes using your ingredients...",
  "ingredients": ["tomatoes", "basil", "mozzarella"],
  "recipes": [
    {
      "title": "Caprese Salad",
      "ingredients": ["tomatoes", "mozzarella", "basil", "olive oil"],
      "instructions": ["Slice tomatoes...", "Layer with mozzarella..."],
      "prep_time_min": 10,
      "cook_time_min": 0,
      "source_url": "https://spoonacular.com/recipes/..."
    }
  ],
  "metadata": {
    "tools_called": ["search_recipes", "get_recipe_information_bulk"],
    "model": "gemini-3-flash-preview",
    "response_time_ms": 2340
  }
}
```

#### Example 2: Multi-Turn Conversation with Preferences

```bash
# Turn 1: Express dietary preference
curl -X POST http://localhost:7777/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am vegetarian and love Italian food",
    "session_id": "user-123"
  }'

# Turn 2: Follow-up without repeating preferences
curl -X POST http://localhost:7777/api/agents/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have potatoes and garlic. What can I make?",
    "session_id": "user-123"
  }'
```

Agent remembers: vegetarian + Italian preferences from Turn 1, applies them in Turn 2.

#### Example 3: Image Upload (Base64)

```bash
# Encode image to base64
IMAGE_BASE64=$(base64 -i path/to/image.jpg)

curl -X POST http://localhost:7777/api/agents/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"${IMAGE_BASE64}\",
    \"message\": \"What recipes can I make with these ingredients?\",
    \"session_id\": \"user-123\"
  }"
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GEMINI_API_KEY` | string | **required** | Google Gemini API key (vision model) |
| `SPOONACULAR_API_KEY` | string | **required** | Spoonacular recipe API key |
| `GEMINI_MODEL` | string | `gemini-3-flash-preview` | Vision model (fast, cost-effective). For best results: `gemini-3-pro-preview` |
| `PORT` | int | `7777` | Server port |
| `MAX_HISTORY` | int | `3` | Conversation turns to keep in memory |
| `MAX_IMAGE_SIZE_MB` | int | `5` | Maximum image upload size |
| `MIN_INGREDIENT_CONFIDENCE` | float | `0.7` | Confidence threshold for detected ingredients (0.0-1.0) |
| `IMAGE_DETECTION_MODE` | string | `pre-hook` | Ingredient detection mode: `pre-hook` (fast, processes before agent) or `tool` (agent control) |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_TYPE` | string | `text` | Log format (text, json) |
| `DATABASE_URL` | string | *optional* | PostgreSQL connection (uses SQLite if not set) |

### Database Configuration

**Development (Default):**
```bash
# Uses SQLite automatically
# Database file: agno.db (created on first run)
```

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



## API Reference

### POST /api/agents/chat

Send a message and get recipe recommendations.

**Request Schema (RecipeRequest):**
```json
{
  "ingredients": ["string"] - Array of 1-50 ingredients, each 1-100 chars (required),
  "diet": "string" - Dietary preference like 'vegetarian', 'vegan', etc. (1-50 chars, optional),
  "cuisine": "string" - Cuisine preference like 'Italian', 'Asian', etc. (1-50 chars, optional),
  "meal_type": "string" - Meal type like 'breakfast', 'dinner', etc. (1-50 chars, optional),
  "intolerances": "string" - Comma-separated allergies like 'gluten,dairy,nuts' (1-100 chars, optional)
}
```

**Validation Rules:**
- `ingredients`: List with 1-50 items; each item stripped of whitespace and validated to 1-100 chars non-empty strings
- `diet`, `cuisine`, `meal_type`: Optional; if provided, 1-50 chars
- `intolerances`: Optional; if provided, 1-100 chars
- All string fields: Whitespace automatically trimmed (`str_strip_whitespace=True`)

**Response Schema (RecipeResponse):**
```json
{
  "response": "string" - LLM-generated conversational response (1-5000 chars, required),
  "recipes": [
    {
      "title": "string" - Recipe name (1-200 chars, required),
      "description": "string" - Brief description (max 500 chars, optional),
      "ingredients": ["string"] - Ingredient list with quantities (1-100 items, required),
      "instructions": ["string"] - Step-by-step cooking instructions (1-100 steps, required),
      "prep_time_min": integer - Preparation time in minutes (0-1440, i.e., 0-24 hours, required),
      "cook_time_min": integer - Cooking time in minutes (0-1440, i.e., 0-24 hours, required),
      "source_url": "string" - URL to original recipe source (must start with http:// or https://, optional)
    }
  ] - List of up to 50 recipes (optional, defaults to empty),
  "ingredients": ["string"] - Detected/provided ingredients list (max 100 items, optional),
  "preferences": {
    "diet": "string",
    "cuisine": "string",
    "meal_type": "string",
    "intolerances": "string"
  } - User preferences extracted from conversation (optional),
  "reasoning": "string" - Explanation of agent's decision-making (max 2000 chars, optional),
  "session_id": "string" - Session identifier for conversation continuity (1-100 chars, optional),
  "run_id": "string" - Unique ID for this agent execution (1-100 chars, optional),
  "execution_time_ms": integer - Total execution time in milliseconds (0-300000, i.e., 0-5 min, required)
}
```

**Validation Rules:**
- `response`: Required non-empty string (1-5000 chars); automatically trimmed
- `recipes`: Optional list of up to 50 Recipe objects
- Each `Recipe.prep_time_min` and `Recipe.cook_time_min`: 0-1440 minutes (0-24 hours)
- Cross-field validation: Total cooking time (prep + cook) must not exceed 1440 minutes
- `Recipe.source_url`: Optional; if provided, must start with `http://` or `https://`
- All string fields: Whitespace automatically trimmed
- `execution_time_ms`: 0-300000 milliseconds (0-5 minutes)

**Error Responses:**
- `400 Bad Request` - Malformed JSON, missing required fields
- `413 Payload Too Large` - Image exceeds MAX_IMAGE_SIZE_MB
- `422 Unprocessable Entity` - Off-topic request (guardrail), or other business logic error
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

### Integration Tests (Real APIs) - Phase 3

```bash
make eval
```

**Status:** Integration tests use **Agno evals framework** (AgentOS built-in evaluation system) and are currently under development (Phase 3).

When complete, tests will include:
- End-to-end ingredient detection (requires GEMINI_API_KEY)
- Recipe recommendation flows (requires SPOONACULAR_API_KEY)
- Multi-turn conversations with session memory
- Preference persistence
- Guardrail behavior
- Error handling

**Note:** Integration tests require valid API keys and internet connection.

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
│   └── integration/       # Integration tests (real APIs, Agno evals)
│       ├── test_e2e.py
│       └── test_api.py
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

This is a code challenge project demonstrating production-quality GenAI system design.

---

**Questions or Issues?** See [Troubleshooting](#troubleshooting) section above.
