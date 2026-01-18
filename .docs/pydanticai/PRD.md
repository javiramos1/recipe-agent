# Product Requirements Document (PRD)

## Project Title
**Image-Based Recipe Recommendation Service (GenAI, MCP-based)**

---

## Purpose & Context

This project implements a **production-quality GenAI application** that generates recipe recommendations from **images of ingredients**, optionally combined with **user preferences** (e.g. “quick vegetarian lunch”).

The goal is to demonstrate:
- Practical, modern GenAI system design
- Multimodal reasoning (vision + text)
- Tool orchestration using MCP
- Structured outputs, validation, and guardrails
- Production-oriented engineering practices (observability, testing, documentation)

This is **not a demo notebook** — it is designed as a **reusable service** that could be integrated into a larger system.

---

## In-Scope Functionality

### Core Capabilities
1. Accept ingredient input via:
   - Image (URL or base64 bytes)
   - Text (explicit ingredient list)
2. Detect ingredients using a **vision-capable LLM**
3. Generate recipe recommendations using detected ingredients
4. Incorporate **user preferences and nuances**
5. Maintain **short-term conversational context** (session-based)
6. Enforce **domain guardrails** (recipes only)
7. Provide **structured, explainable outputs**
8. Expose functionality via a **FastAPI JSON API**

---

## Out of Scope

- User authentication / authorization
- Persistent storage (database)
- UI / frontend
- Image preprocessing or segmentation
- Nutritional analysis or shopping lists
- Internationalization
- Rate limiting / throttling

---

## High-Level System Overview

The system consists of:

1. **FastAPI Application**
   - Public REST API
   - Stateless HTTP interface

2. **Stateful Orchestrator (PydanticAI Agent)**
   - Maintains session memory
   - Applies guardrails and decision logic
   - Calls tools (MCP servers)

3. **Ingredient Detection MCP (Custom)**
   - Vision-based ingredient extraction
   - Stateless

4. **Recipe MCP (External)**
   - Generates recipes from ingredients
   - Stateless

5. **Observability Layer**
   - Langfuse tracing and evaluations

---

## Functional Requirements

### FR-1: REST API Input Handling

The API **must** support two optional image input methods:
- `image_url` (string)
- `image_base64` (string, base64-encoded bytes)

**Image Constraints:**
- Supported formats: JPEG, PNG
- Maximum size: 5MB (configurable via `MAX_IMAGE_SIZE_MB` in config.py)
- API generates unique `image_id` for tracking

**Input Rules:**
- At least **one** of: image_url, image_base64, or explicit ingredients in user_message must be provided
- Ingredients can be inferred from user_message text or extracted from images
- If both `image_url` and `image_base64` provided, return 400 error
- If multiple sources are provided, the orchestrator prioritizes based on context

**Conceptual Request Payload:**
- `chat_id`: optional string (session identifier)
- `user_message`: free-form text (preferences, ingredients, or questions)
- `image_url`: optional URL to ingredient image
- `image_base64`: optional base64-encoded image bytes

**User Preferences in Messages:**
Preferences (dietary restrictions, cuisine type, meal type, intolerances) are extracted from `user_message` text by the orchestrator, not as a separate field.
- Examples: "What quick Italian vegetarian recipes?", "Recipes with no peanuts", "Dessert ideas with chocolate"
- The orchestrator's LLM infers these preferences and passes them to the recipe MCP

---

### FR-2: Session-Based Conversation Memory

The system maintains **short-term memory** per conversation.

**Requirements:**
- Identified by `chat_id`
- If `chat_id` is missing, generate a new one and return it in the response
- Client is responsible for resending `chat_id`

**Memory Constraints:**
- In-memory only (no persistence)
- Configurable maximum history via `MAX_HISTORY` environment variable (default: 3)
- Oldest entries are evicted when limit is reached

**Message Metadata Handling:**
- Each conversation message is stored with attached metadata:
  - Detected ingredients (from image or text parsing)
  - User preferences extracted from message (diet, cuisine, intolerances, meal type)
- **Images (base64 data) are NEVER stored** - only detected ingredients and preferences are retained
- This reduces memory footprint and avoids redundant storage once ingredients are extracted
- Preferences persist in chat history and can be referenced in follow-up questions
- Example metadata on a message: `{ingredients: ["tomato", "onion"], diet: "vegetarian", cuisine: "italian"}`

---

### FR-3: Ingredient & Preference Tracking

The system tracks ingredients and user preferences per conversation message.

**Per-Message Metadata:**
- **Ingredients**: Detected from image or inferred from user_message text
- **Preferences**: Extracted from user_message (diet type, cuisine, meal type, intolerances)

This allows the orchestrator to:
- Reference previously mentioned ingredients in follow-up questions
- Apply user preferences consistently across the conversation
- Support contextual follow-ups like "What about desserts instead?"
- Reuse preferences from earlier messages for new recipe searches

---

### FR-4: Ingredient Detection (Vision MCP)

A custom **FastMCP server** provides ingredient detection using vision capabilities.

**Requirements:**
- Runs locally using Gemini vision API
- Input: Raw image bytes (base64)
- Output: Structured response containing:
  - List of detected ingredients
  - Image description (generated by vision LLM)
  - Confidence scores for each ingredient
- Stateless (no memory between calls)
- Uses Gemini vision model (configurable via `GEMINI_MODEL`)
- **Application fails at startup if unable to connect to this vision service**

**Confidence Filtering:**
- Applied locally with minimum confidence threshold via `MIN_INGREDIENT_CONFIDENCE` environment variable
- Ingredients below threshold are filtered out
- Default threshold: 0.7 (configurable in config.py)

---

### FR-5: Recipe Generation (Spoonacular MCP)

The system integrates an **external MCP server** ([spoonacular-mcp](https://github.com/ddsky/spoonacular-mcp)) to generate recipes.

**Requirements:**
- Runs via npx without checking out the repository
- Requires `SPOONACULAR_API_KEY` environment variable for API access
- Input:
  - Search query (ingredients as comma-separated string)
  - Optional filters: diet, intolerances, meal type (main course, dessert, etc.), cuisine type
- Output:
  - Recipe recommendations with structured data (title, description, ingredients, instructions, prep/cook times)
- Stateless (no memory between calls)
- Receives explicit ingredient list and extracted preferences from orchestrator
- **Application fails at startup if unable to connect to this MCP server**

**Spoonacular Recipe Search Tool:**
The MCP provides `search_recipes` tool with parameters:
- `query` (required): Ingredient list or recipe query
- `diet` (optional): "vegetarian", "vegan", "gluten-free", etc.
- `intolerances` (optional): Comma-separated intolerances (peanuts, dairy, shellfish, etc.)
- `type` (optional): Meal type (main course, side dish, dessert, appetizer, etc.)
- `cuisine` (optional): Cuisine type (italian, mexican, chinese, indian, etc.)
- `number` (optional, default 10): Number of results (1-100)

**Implementation:**
- Use PydanticAI's FastMCP client with npx transport
- Pass extracted preferences as parameters to `search_recipes` tool

---

### FR-6: Orchestrator Decision Logic & System Prompt

The orchestrator is the **central intelligence layer** that manages all decision-making using a detailed system prompt with comprehensive instructions.

**Core Responsibilities:**

1. **Apply Domain Guardrails**
   - Only answer recipe-related questions
   - Refuse or politely redirect unrelated queries
   - Do not call tools if request is clearly off-topic

2. **Understand User Intent**
   - Determine if this is a new recipe request, follow-up question, or conversation acknowledgment
   - Identify whether user is asking for recipes, clarifying ingredients, or adjusting preferences
   - Example intents: "Give me recipes with these ingredients", "What about vegetarian options?", "More desserts please"

3. **Determine Ingredient Source**
   - Extract ingredients from current `user_message` if explicitly mentioned
   - If image provided, call vision service to detect ingredients
   - Reference ingredients from chat history for context (e.g., follow-ups like "what about vegan versions?")
   - If **no ingredients available** → refuse and ask user to provide ingredients or image

4. **Extract User Preferences**
   - From `user_message`, extract: diet type, cuisine, meal type, intolerances
   - Examples: "Italian vegetarian" → diet="vegetarian", cuisine="italian"
   - Preserve preferences from history when relevant for follow-ups

5. **Tool Call Decision**
   - **Vision (Ingredient Detection)**: Call ONLY if image provided and ingredients need detection
   - **Recipe Search**: Call when ingredients available AND user is requesting recipes
     - Pass extracted preferences as parameters (diet, cuisine, type, intolerances)
     - Example: "Italian vegetarian recipes with tomato and basil" → query="tomato,basil", diet="vegetarian", cuisine="italian"
   - Not all requests need tools: simple acknowledgments ("thanks") don't require API calls

6. **Craft Final Response**
   - Ground in tool outputs (no hallucinating ingredients or recipes)
   - Incorporate chat history and established preferences
   - Reference conversation naturally ("As we discussed, you wanted vegetarian...")
   - Be concise, helpful, and relevant

**System Prompt Requirements:**

The system prompt must explicitly teach the orchestrator to:
- Use conversation context to understand if this is a new request or follow-up
- Extract and track diet, cuisine, meal type, and intolerances from user messages
- Pass the correct parameters to `search_recipes` tool
- Remember preferences across conversation turns (e.g., "You wanted vegetarian, here are options for...")
- Handle edge cases: image upload, preference changes, recipe refinements

**Tool Usage Guidelines:**

1. **Ingredient Detection MCP**: Only call when an image is sent in the current user message to extract ingredients
2. **Recipe MCP**: Call when asked about recipes (main goal), follow-up questions can skip this tool call but should be called most of the time to get more ideas. Orchestrator can update recipes from Recipe MCP based on previous history, or call Recipe MCP multiple times to find the best recipe.

**Preference Extraction Examples:**
- "Italian vegetarian recipes" → diet="vegetarian", cuisine="italian"
- "Gluten-free dessert ideas" → intolerances="gluten", type="dessert"
- "Quick vegan lunch" → diet="vegan", type="main course"
- "No peanuts please" → intolerances="peanuts"

---

### FR-7: Guardrails & Domain Boundaries

The system enforces strict recipe-focused boundaries.

**Recipe-Related (✅ In-Scope):**
- Generating recipes from ingredients
- Ingredient substitutions or modifications
- Dietary accommodations (vegan, vegetarian, gluten-free, etc.)
- Cuisine and meal type recommendations
- Cooking techniques and methods
- Intolerances and allergies in recipes

**Not Recipe-Related (❌ Out-of-Scope):**
- Nutritional analysis or calorie counting
- Agricultural/farming information
- Grocery shopping or meal planning services
- Food history or cultural trivia
- Personal dietary advice or medical information
- General conversation unrelated to recipes

**Guardrail Behavior:**
- If request is off-topic, respond with a clear, polite message: "I'm designed to help with recipes. Could you ask about recipes instead?"
- Do not call tools for off-topic requests
- Guide user toward providing ingredients or recipe preferences
- Allow recipe-related follow-ups even if tangentially related (e.g., "Do these ingredients have allergens?" → reframe to "What recipes avoid X allergen?")

---

### FR-8: Structured Outputs

All internal and external LLM interactions must use:
- Pydantic models
- Explicit schemas
- Validation with retries where appropriate

The final API response must include:
- Detected ingredients
- Recommended recipes
- Chat ID
- Metadata / grounding information (tools called, model used, response time)

---

### FR-9: Configuration Management

Configuration must be centralized in `config.py`.

**Configuration Loading:**
- Use `.env` files for local development (with python-dotenv)
- `config.py` must read from both `.env` files AND system environment variables
- System environment variables take precedence over `.env` file values
- Include `.env.example` in repository (without sensitive values)
- Add `.env` to `.gitignore` to prevent committing secrets

**Required environment variables:**
- `GEMINI_API_KEY` - API key for Gemini model access (vision)
- `SPOONACULAR_API_KEY` - API key for Spoonacular recipe service
- `GEMINI_MODEL` - Model name (default: `gemini-1.5-flash`)
- `MAX_HISTORY` - Maximum conversation history entries (default: 3)
- `MAX_IMAGE_SIZE_MB` - Maximum image upload size in MB (default: 5)
- `MIN_INGREDIENT_CONFIDENCE` - Minimum confidence for ingredient detection (default: 0.7)
- `LANGFUSE_PUBLIC_KEY` - Langfuse public key (optional)
- `LANGFUSE_SECRET_KEY` - Langfuse secret key (optional)

**Rules:**
- No hardcoded secrets in code
- All configuration through environment variables or `.env` files
- Sensible defaults for non-sensitive settings

---

### FR-10: Observability & Tracing

**Langfuse integration is optional** - if credentials are not provided, the system logs a warning and continues without tracing.

When Langfuse is configured, it provides:

**Tracing:**
- Orchestrator runs (decision flow, tool calls)
- Individual MCP tool invocations
- Latency measurements for each component
- Error tracking and debugging context

**Evaluation:**
- Ingredient detection accuracy (basic metrics)
- Recipe relevance scoring (LLM-as-judge)

**Trace Metadata:**
- Chat ID
- Tools called
- Model used
- Response time
- User preferences and context

---

### FR-11: Testing

**Unit Tests**
- Schema validation
- Orchestrator decision logic (mocked tools)
- Guardrail behavior

**Integration Tests (Langfuse-based)**
- End-to-end runs using test images
- Executed via Makefile
- Results logged as Langfuse evaluations

---

### FR-12: CLI Utility

A **bash script** (`scripts/cli.sh`) provides convenient testing interface.

**Functionality:**
- Read images from local directory (default: `images/`)
- Encode images to base64
- Send HTTP POST requests to local API (`http://localhost:8000/recommend-recipes`)
- Format and display JSON responses
- Support conversation flow with `chat_id` persistence

**Usage Examples:**
```bash
# First call - new session with image
./scripts/cli.sh images/vegetables.jpg

# Follow-up - reuse chat_id for context
./scripts/cli.sh images/fruits.jpg <chat_id_from_previous>

# Text-only follow-up with preference change
./scripts/cli.sh "" <chat_id> "What about vegetarian versions?"

# Text-only recipe request with ingredients
./scripts/cli.sh "" <new_chat_id> "I have chicken, rice, and broccoli. Make dinner recipes."

# Follow-up asking for different cuisine
./scripts/cli.sh "" <chat_id> "What about Italian versions instead?"

# Request for specific meal type
./scripts/cli.sh "" <chat_id> "Show me dessert options with these ingredients."

# Dietary restriction follow-up
./scripts/cli.sh "" <chat_id> "Are there gluten-free alternatives?"

# Multiple preference combination
./scripts/cli.sh "" <new_chat_id> "Quick vegan lunch ideas with tofu and vegetables."
```

**Features:**
- Automatic base64 encoding
- Pretty-print JSON responses with `jq`
- Support for JPEG and PNG formats
- Error handling for missing files
- Display metadata (tools called, response time)

**Purpose:**
- Manual testing during development
- Reviewer convenience for quick testing
- Example usage for integrators
- Demo purposes

---

### FR-13: Developer Experience

The repository must include:

**Makefile with Commands:**
- `make setup` - Install dependencies and configure environment
- `make dev` - Run development server with hot reload
- `make run` - Run production server
- `make test` - Run unit tests
- `make eval` - Run integration tests with Langfuse evaluations

**Documentation:**
- Clear README with setup and usage instructions
- Copilot / AI assistant instructions (`.github/copilot-instructions.md`)
- Clean, consistent naming and module structure
- Inline code comments for complex logic

---

### FR-14: Error Handling & Response Format

**Success Response (HTTP 200):**
```json
{
  "chat_id": "string",
  "response": "string (synthesized natural language response using ingredients and recipes)",
  "ingredients": ["ingredient1", "ingredient2"],
  "recipes": [...],
  "metadata": {
    "tools_called": ["ingredient_detection", "recipe_generation"],
    "model": "gemini-1.5-flash",
    "response_time_ms": 1234
  }
}
```

**Error Response Format:**
- `400 Bad Request` - Invalid input (missing required fields, image too large, invalid format)
- `413 Payload Too Large` - Image exceeds MAX_IMAGE_SIZE_MB
- `422 Unprocessable Entity` - Valid format but business logic failure (e.g., guardrails triggered)
- `500 Internal Server Error` - Unexpected system errors

**Error Response Schema:**
```json
{
  "error": "string (error type)",
  "message": "string (human-readable explanation)",
  "chat_id": "string (if available)"
}
```

---

## Non-Functional Requirements

### NFR-1: Code Quality
- Single-responsibility functions
- Clear naming (no generic verbs)
- Modular structure
- Reusable components

### NFR-2: Reliability
- Graceful handling of LLM failures
- Retries where appropriate
- Deterministic validation of outputs

### NFR-3: Performance
- Designed for local execution
- Response times captured and reported
- No unnecessary LLM calls

### NFR-4: Maintainability
- Easy to extend with new MCP tools
- Clear separation between orchestration and tools
- Minimal coupling

### NFR-5: Security
- No secrets in code
- No logging of raw image bytes

---

## Success Criteria

A reviewer should be able to:

**Functional Success:**
- Run the API locally using `make setup && make dev`
- Send an image via CLI script and receive structured recipe recommendations
- Verify ingredients are correctly detected from images (>80% accuracy on clear images)
- Test conversational flow with follow-up questions using same `chat_id`
- Confirm guardrails prevent off-topic requests

**Technical Success:**
- All unit tests pass (`make test`)
- Integration tests with sample images execute successfully (`make eval`)
- Langfuse traces are visible (when configured) with proper metadata
- Response times are reasonable (<10 seconds for typical requests)
- Code is well-structured, documented, and follows Python best practices

**Extensibility:**
- Understand system architecture from documentation
- Easily identify where to add new MCP tools or modify orchestration logic
- Clear separation of concerns between API, orchestrator, and tools
