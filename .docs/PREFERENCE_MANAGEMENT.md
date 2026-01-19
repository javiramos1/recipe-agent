# Preference Management System

## Overview

The Recipe Recommendation Agent uses **Agno's automatic user memory system** to manage user preferences across conversations. This document explains how preferences are extracted, stored, and applied.

## Architecture

### 1. Input Schema: Minimal Conversational Validation

The agent uses `ChatMessage` as input_schema (not structured preference fields):

```python
class ChatMessage(BaseModel):
    message: str  # Natural language user input
    images: Optional[List[str]] = None  # Optional image data
```

**Why minimal?**

- Preferences emerge from natural conversation, not pre-structured input
- Examples: "I'm vegetarian", "I love Italian food", "I'm allergic to peanuts"
- No need to enforce preference format at validation time
- Agent (LLM) extracts meaning from conversational context

### 2. Memory Storage: Agno User Memory System

Configured in `agent.py`:

```python
agent = Agent(
    # ... other config ...
    enable_user_memories=True,  # Automatic memory extraction and storage
    add_history_to_context=True,  # Session history in LLM context
    num_history_runs=3,  # Keep last 3 conversation turns
)
```

**What gets stored automatically:**
- User preferences mentioned in messages: diet, cuisine, allergies, meal preferences
- Conversation context and history
- Extracted metadata about user preferences

**Storage backend:**
- Development: SQLite + LanceDB (file-based, zero setup)
- Production: PostgreSQL + pgvector (via DATABASE_URL)

### 3. Memory Retrieval: Automatic Context Injection

When the agent processes a request, Agno automatically:

1. **Loads session history** from database (last N turns)
2. **Injects user memories** into LLM context as structured data
3. **Injects conversation history** for continuity
4. **LLM uses this context** when:
   - Extracting ingredients from message
   - Deciding what tool parameters to use
   - Generating responses

**Example context injection:**

```
<user_memories>
- User prefers vegetarian recipes (mentioned in turn 1)
- User loves Italian cuisine (mentioned in turn 2)
- User is allergic to shellfish (mentioned in turn 3)
</user_memories>

<conversation_history>
Turn 1: User: "I'm vegetarian"
Turn 2: User: "I love Italian food"
Turn 3: User: "Show me recipes"
</conversation_history>

Current message: "Show me recipes for tomatoes and basil"
```

## Preference Flow: Three Conversation Examples

### Example 1: First Message with Image

```
User API Request:
{
  "message": "What can I make with these?",
  "images": ["base64_image_data"]
}

Flow:
1. Validate input (ChatMessage schema) ✓ passes
2. Pre-hook extracts ingredients from image: [tomato, basil, mozzarella]
3. Pre-hook appends to message: "What can I make with these?\n\n[Detected Ingredients] tomato, basil, mozzarella"
4. LLM processes enriched message
5. LLM calls: search_recipes(
     ingredients=[tomato, basil, mozzarella],
     number=3
   )  # No preferences yet (no stored memories)
6. Response: 3 recipes using detected ingredients
7. Agno stores: First turn in session memory

Agent Response:
{
  "response": "Found 3 great recipes using tomato, basil, and mozzarella...",
  "recipes": [...],
  "ingredients": ["tomato", "basil", "mozzarella"]
}
```

### Example 2: Follow-up with Preference Mention

```
User API Request:
{
  "message": "I'm actually vegetarian, show me only vegetarian options"
}

Flow:
1. Validate input (ChatMessage schema) ✓ passes
2. Agno loads session memory:
   - Previous turn: ingredients=[tomato, basil, mozzarella]
   - Conversation history: First user question
3. LLM reads enriched context:
   - Current message: "I'm actually vegetarian..."
   - Previous message: "What can I make with these?"
   - Detected ingredients from turn 1: tomato, basil, mozzarella
4. LLM extracts: User is now stating vegetarian preference
5. LLM calls: search_recipes(
     ingredients=[tomato, basil, mozzarella],
     diet="vegetarian",  # ← Extracted from current message
     number=3
   )
6. Agno automatically stores: User prefers vegetarian (in user_memories)
7. Response: 3 vegetarian recipes

Agent Response:
{
  "response": "Found 3 vegetarian recipes with your ingredients...",
  "recipes": [...],
  "preferences": {"diet": "vegetarian"}
}
```

### Example 3: Third Message - Preferences Applied Automatically

```
User API Request:
{
  "message": "Actually, I love Italian cuisine. Show me Italian options"
}

Flow:
1. Validate input (ChatMessage schema) ✓ passes
2. Agno loads session memory:
   - User preferences: {"diet": "vegetarian"}  ← Stored from turn 2
   - Last turn ingredients: [tomato, basil, mozzarella]
   - Conversation history: All 3 turns
3. LLM reads enriched context:
   - Current message: "I love Italian cuisine..."
   - User memories: vegetarian, (new) Italian cuisine preference
   - Previous turn: Used tomato, basil, mozzarella with vegetarian filter
4. LLM extracts: User now wants Italian cuisine
5. LLM calls: search_recipes(
     ingredients=[tomato, basil, mozzarella],
     diet="vegetarian",  # ← From stored memory (turn 2)
     cuisine="Italian",  # ← From current message
     number=3
   )
6. Agno stores: User loves Italian cuisine (added to user_memories)
7. Response: 3 Italian vegetarian recipes

Agent Response:
{
  "response": "Perfect! Here are 3 Italian vegetarian recipes with your ingredients...",
  "recipes": [...],
  "preferences": {"diet": "vegetarian", "cuisine": "Italian"}
}
```

## How System Instructions Guide Preference Application

From `src/prompts/prompts.py`:

```python
## When to apply preferences:
- When calling search_recipes: Always include diet, cuisine, intolerances parameters based on stored preferences
- Example: If memory shows "user_diet=vegetarian", include diet="vegetarian" in search_recipes call
- Apply ALL stored preferences automatically (unless user explicitly asks to ignore them)
- If user changes a preference mid-conversation, acknowledge it and apply the updated preference going forward

## Reference in responses:
- Mention preferences naturally: "Following up on your vegetarian preference from earlier..."
- If user changes preferences: "Got it, I'll update your preferences to vegan and re-search"
```

## Technical Implementation

### Agent Configuration (agent.py)

```python
agent = Agent(
    model=Gemini(...),
    db=db,  # SQLite or PostgreSQL
    tools=[mcp_tools],
    pre_hooks=pre_hooks,
    input_schema=ChatMessage,  # Minimal validation
    output_schema=RecipeResponse,
    instructions=system_instructions,  # Defines preference behavior
    
    # Memory settings
    add_history_to_context=True,  # Inject conversation history
    num_history_runs=3,  # Last 3 turns
    enable_user_memories=True,  # Automatic preference extraction
    enable_session_summaries=True,  # Auto-summarize long conversations
    compress_tool_results=True,  # Compress verbose tool outputs
)
```

### System Instructions Guidance

The system instructions (in `prompts.py`) tell the LLM:

1. **How to extract preferences:**
   - From explicit statements: "I'm vegetarian"
   - From implicit requests: "No shellfish please"
   - From context: "Italian recipes"

2. **Where to find stored preferences:**
   - User memories (automatically injected by Agno)
   - Conversation history (last N turns)
   - Current message (explicit new preferences)

3. **How to apply preferences to tool calls:**
   - Check conversation history for ingredient sources
   - Check user memories for stored preferences
   - Pass preferences as parameters to search_recipes
   - Always filter by allergies/intolerances

4. **How to communicate about preferences:**
   - Acknowledge stored preferences naturally
   - Ask for clarification if uncertain
   - Update preferences if user changes them
   - Reference previous preferences without re-asking

## Key Advantages of This System

✅ **No hardcoded preference fields** - Flexible and extensible
✅ **Natural conversation flow** - Extract from natural language
✅ **Automatic memory management** - Agno handles persistence
✅ **Minimal input validation** - ChatMessage schema is tiny
✅ **Multi-turn awareness** - Full conversation context available
✅ **Preference persistence** - Across restarts with same session_id
✅ **LLM-driven routing** - Agent decides when/how to apply preferences
✅ **Graceful degradation** - Works with or without stored preferences

## Testing Preferences

See `tests/unit/test_models.py::TestChatMessage` for input validation tests.

Example test cases:
- Valid message with images (edge case: 10 images)
- Valid message without images
- Preferences applied in follow-up turns
- Preferences changed mid-conversation
- Preferences persisted across session restarts

Integration tests (in `tests/integration/`) would verify:
- Image → preference extraction → tool call with preference parameter
- Follow-up turn uses stored preference without re-asking
- Preference changes are acknowledged and applied
- Multi-turn conversation maintains preference consistency
