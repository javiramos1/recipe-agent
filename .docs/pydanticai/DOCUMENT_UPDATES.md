# PRD & DESIGN Document Updates Summary

**Date:** 11 January 2026  
**Status:** ✅ All updates applied and verified

---

## 📋 Overview

Both PRD.md and DESIGN.md have been comprehensively updated to reflect:
1. **MCP Change**: kitchen-mcp → spoonacular-mcp (via npx, no local checkout)
2. **Architecture Change**: Per-message metadata with preferences + ingredients
3. **Orchestrator Enhancement**: Intelligent preference extraction and preservation
4. **Configuration Update**: Added SPOONACULAR_API_KEY as required variable
5. **Guardrails Clarification**: Detailed recipe-related scope with examples

---

## 🔄 Key Architecture Changes

### 1. MCP Selection: kitchen-mcp → spoonacular-mcp

**Impact:**  Easier deployment, no repository checkout required

| Aspect | Before | After |
|--------|--------|-------|
| Setup | Clone repo locally | Run directly via npx |
| Command | `npx kitchen-mcp` with cwd | `npx spoonacular-mcp` |
| Input | ingredients[], preferences string | search_recipes tool with parameters |
| Parameters | Simple | query, diet, cuisine, type, intolerances, number |

**Files Updated:**
- PRD FR-5: Recipe Generation requirements
- DESIGN 11.2: Recipe MCP client implementation
- DESIGN 16: Makefile (removed kitchen-mcp clone)
- DESIGN 19: Implementation phases Phase 4

---

### 2. Configuration: Added SPOONACULAR_API_KEY

**New Requirements:**
```bash
GEMINI_API_KEY=your_gemini_key_here          # For Vision
SPOONACULAR_API_KEY=your_spoonacular_key_here # For Recipes
```

**Both keys required at startup** (fail-fast validation)

**Files Updated:**
- PRD FR-9: Configuration Management
- DESIGN 12: Config implementation with validation

---

### 3. Memory Architecture: Per-Message Metadata

**Before:** Image metadata stored separately  
**After:** Each message includes:
- `ingredients`: detected/discussed ingredients
- `preferences`: extracted user preferences (diet, cuisine, intolerances, meal_type)
- `timestamp`: message creation time

**Benefit:** Preferences persist across conversation for contextual follow-ups

**Example:**
```python
Message 1:
  text: "Italian recipes with tomato and basil"
  ingredients: ["tomato", "basil"]
  preferences: {diet: "vegetarian", cuisine: "italian"}

Follow-up:
  text: "What about gluten-free options?"
  # Orchestrator references previous preferences
```

**Files Updated:**
- PRD FR-2: Session-Based Conversation Memory
- PRD FR-3: Ingredient & Preference Tracking (renamed from Image Context)
- DESIGN 3.4: Memory Design Rationale
- DESIGN 8: Memory Model
- DESIGN 10: Core Domain Models

---

### 4. Orchestrator Intelligence: Preference Handling

**Core Responsibilities Enhanced:**

1. **Intent Detection**: Determine if request is:
   - New recipe request
   - Follow-up question
   - Simple acknowledgment

2. **Preference Extraction**: Parse from user_message:
   - `diet`: "vegetarian", "vegan", "gluten-free", etc.
   - `cuisine`: "italian", "mexican", "asian", etc.
   - `type`: "main course", "dessert", "appetizer", etc.
   - `intolerances`: comma-separated dietary restrictions

3. **Preference Preservation**: Remember across turns

4. **Tool Parameter Passing**: Call `search_recipes(query, diet, cuisine, type, intolerances, number)`

**Files Updated:**
- PRD FR-6: Orchestrator Decision Logic (significantly expanded)
- DESIGN 9: Orchestrator Logic
- DESIGN 11.2: Recipe Client tool parameters
- DESIGN 20: Critical notes on preference handling

---

### 5. Vision Service Simplification

**Before:** Custom FastMCP server  
**After:** Direct Gemini Vision integration

| Aspect | Before | After |
|--------|--------|-------|
| Type | FastMCP server | Local service |
| Process | Separate process | Direct SDK call |
| Image ID | Tracked and returned | Not needed |
| Filtering | Returns filtered_ingredients flag | Applied internally |

**Files Updated:**
- PRD FR-4: Ingredient Detection
- DESIGN 11.1: Vision Service
- DESIGN 5: Folder structure (vision.py not ingredient_recognition.py)

---

### 6. Guardrails: Specific Boundaries

**In-Scope (✅):**
- Generating recipes from ingredients
- Ingredient substitutions/modifications
- Dietary accommodations (vegan, vegetarian, gluten-free)
- Cuisine and meal type recommendations
- Cooking techniques and methods
- Intolerances and allergies in recipes

**Out-of-Scope (❌):**
- Nutritional analysis or calorie counting
- Agricultural/farming information
- Grocery shopping or meal planning services
- Food history or cultural trivia
- Personal dietary advice or medical information

**Files Updated:**
- PRD FR-7: Guardrails & Domain Boundaries (newly detailed)

---

### 7. CLI Utility: Enhanced Examples

**New Usage Examples:**
```bash
# First call - new session with image
./scripts/cli.sh images/vegetables.jpg

# Follow-up - reuse chat_id for context
./scripts/cli.sh images/fruits.jpg <chat_id_from_previous>

# Text-only follow-up with preference change
./scripts/cli.sh "" <chat_id> "What about vegetarian versions?"
```

**Features:**
- Automatic base64 encoding
- Pretty-print JSON responses with jq
- Support for JPEG and PNG
- Error handling for missing files
- Display metadata (tools called, response time, preferences)

**Files Updated:**
- PRD FR-12: CLI Utility (added usage examples)
- DESIGN 15: CLI Script (enhanced with conversation flow)

---

## 📝 Document Changes Summary

### PRD.md Updates

| Section | Type | Changes |
|---------|------|---------|
| FR-1 | Added | Input precedence rule for image handling |
| FR-1 | Added | User preferences in user_message (not separate field) |
| FR-2 | Changed | Image storage → Per-message metadata |
| FR-3 | Renamed | "Image Context Management" → "Ingredient & Preference Tracking" |
| FR-4 | Simplified | Removed image_id; focused on ingredient detection |
| FR-5 | **Major** | kitchen-mcp → spoonacular-mcp with parameter details |
| FR-6 | **Expanded** | 6 core orchestrator responsibilities + system prompt requirements |
| FR-7 | **New** | Detailed guardrail boundaries with examples |
| FR-9 | Added | SPOONACULAR_API_KEY to required environment variables |
| FR-12 | Enhanced | CLI usage examples showing conversation flow |

### DESIGN.md Updates

| Section | Type | Changes |
|---------|------|---------|
| 3.4 | Updated | Memory design emphasizes ingredient + preference persistence |
| 5 | Updated | Folder structure: vision.py and recipe_client.py |
| 5 | Updated | Module responsibilities for new services |
| 10 | Updated | ChatSession model with per-message metadata |
| 11.1 | **Replaced** | "Ingredient Detection MCP" → "Vision Service" (Gemini) |
| 11.2 | **Replaced** | "kitchen-mcp" → "spoonacular-mcp" throughout |
| 11.2 | Added | Detailed search_recipes parameters with descriptions |
| 11.3 | Updated | Startup validation for both Vision API + Spoonacular |
| 12 | Updated | Config requires SPOONACULAR_API_KEY |
| 16 | Removed | kitchen-mcp clone from setup |
| 19 | Updated | Phase 4 focuses on Vision + Recipe Client (not separate servers) |
| 19 | Added | Preference preservation and follow-up testing in Phase 8-10 |
| 20 | **Enhanced** | Critical Do's & Don'ts emphasize preferences + orchestrator |

---

## ✅ What Remains Unchanged (Already Correct)

- ✅ Base64 never stored in memory
- ✅ MCP startup validation (fail-fast pattern)
- ✅ HTTP status codes (400, 413, 422, 500)
- ✅ Response format with metadata
- ✅ Session-based conversation with chat_id
- ✅ FIFO eviction logic for MAX_HISTORY
- ✅ Langfuse optional with graceful degradation
- ✅ Testing strategy (unit + integration)
- ✅ Makefile commands (setup, dev, run, test, eval, clean)
- ✅ Config loading (env vars override .env)

---

## 🎯 Implementation Focus Areas

### 1. Orchestrator System Prompt (CRITICAL)

Must explicitly handle:
```
1. Guardrails: Only recipe-related questions
2. Intent Detection: New request vs follow-up vs acknowledgment
3. Ingredient Extraction: Parse from user_message text
4. Preference Extraction: diet, cuisine, intolerances, meal_type
5. Preference Preservation: Remember across conversation turns
6. Tool Calling: Pass preferences as search_recipes parameters
7. Response Crafting: Ground in tool outputs, reference preferences naturally
```

### 2. Memory Model

Per-message structure:
```python
{
  "role": "user" | "assistant",
  "content": "message text",
  "ingredients": ["tomato", "basil"],
  "preferences": {
    "diet": "vegetarian",
    "cuisine": "italian",
    "intolerances": ["peanuts"],
    "meal_type": "main course"
  },
  "timestamp": "2026-01-11T10:30:00Z"
}
```

### 3. Preference Passing to Spoonacular

```python
search_recipes(
  query="tomato,basil",  # comma-separated ingredients
  diet="vegetarian",
  cuisine="italian",
  type="main course",
  intolerances="peanuts",
  number=10
)
```

### 4. Testing Conversation Flow

Test example:
```
Turn 1: "I have tomatoes and basil, make Italian recipes"
  → Extracts: ingredients=[tomato, basil], diet=vegetarian, cuisine=italian
  → Calls search_recipes with all parameters
  → Stores: {ingredients, preferences} in message metadata

Turn 2: "What about gluten-free options?" (same chat_id)
  → Recognizes: follow-up question (referencing previous request)
  → Preserves: ingredients=[tomato, basil]
  → Updates: adds intolerances=gluten (merges with existing preferences)
  → Calls: search_recipes with merged preferences
```

---

## 📚 Reference Files

- **`.docs/PRD.md`**: Complete product requirements
- **`.docs/DESIGN.md`**: Detailed implementation guide
- **`.github/copilot-instructions.md`**: Development standards
- **`DOCUMENT_UPDATES.md`**: This file (change summary)

---

## 🚀 Next Steps

1. **Verify API Keys**
   - Obtain GEMINI_API_KEY from Google AI Studio
   - Obtain SPOONACULAR_API_KEY from Spoonacular.com

2. **Set Up Environment**
   ```bash
   cp .env.example .env
   # Edit with your API keys
   ```

3. **Follow Implementation Phases** (DESIGN 19)
   - Phases 1-3: Setup, config, models, memory
   - Phase 4: Vision service + Recipe client
   - Phase 5: Orchestrator with enhanced system prompt
   - Phase 6-10: API, testing, validation

4. **Focus on Orchestrator**
   - System prompt must handle all decision logic
   - Preference extraction is core responsibility
   - Memory metadata flows through entire system

---

**Status:** 🟢 All documentation updates complete and consistent with user clarifications
