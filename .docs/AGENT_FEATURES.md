# Agno Agent Features Summary

Quick reference for all Agno Agent capabilities, what we use, and when to use each feature.

## Core Features Matrix

| Feature | Purpose | Status | Default | Extra LLM Calls | Default Model | Use Case |
|---------|---------|--------|---------|-----------------|----------------|----------|
| **Chat History** | Conversation continuity | ✅ Using | Enabled | No | N/A | Reference past messages in current/past sessions |
| **Sessions** | Multi-turn conversations | ✅ Using | Enabled | No | N/A | Persistent conversation threads with session_id |
| **User Memories** | Track user preferences | ✅ Using | Enabled | Yes | AGENT_MNGT_MODEL | Extract dietary restrictions, cuisine preferences |
| **Session Summaries** | Compress long contexts | ✅ Using | Disabled | Yes | AGENT_MNGT_MODEL | Cost-save on long conversations (enable if needed) |
| **Tool Compression** | Reduce tool output size | ✅ Using | Enabled | No | N/A | Shrink verbose API responses in context |
| **Multi-Session History** | Cross-session context | ✅ Using | Enabled (2 sessions) | No | N/A | Long-term preference tracking across conversations |
| **Learning Machines** | Dynamic insight extraction | ✅ Using | Enabled (AGENTIC) | Yes | AGENT_MNGT_MODEL | Save recipe insights, user preferences over time |
| **LearnedKnowledge** | Agent-created insights | ✅ Using | Enabled | Yes | AGENT_MNGT_MODEL | Share learned recipes/patterns globally |
| **Learning Context Injection** | Auto-inject learnings | ✅ Using (False) | Disabled | No | N/A | Control when learnings appear in context |
| **Datetime Context** | Time-aware reasoning | ✅ Using | Enabled | No | N/A | Support temporal queries ("quick weeknight dinners", seasonal recipes) |
| **Location Context** | Location-aware reasoning | ⚠️ Available | Disabled | No | N/A | Support local ingredients, regional cuisines (requires user permission) |
| **Session Caching** | In-memory session cache | ⚠️ Available | Disabled | No | N/A | Performance optimization for single-server deployments |
| **Debug Mode** | Detailed logging & inspection | ⚠️ Available | Disabled | No | N/A | Development/troubleshooting (see compiled system message) |
| **Knowledge Base** | External documents | ❌ Disabled | Disabled | No | N/A | Ground responses in static docs/FAQs |
| **Skills** | Domain expertise packages | ❌ Not Used | N/A | No | N/A | Reusable instruction sets (overkill for recipes) |
| **Culture** | Org-wide principles | ❌ Not Used | N/A | No | N/A | Multi-agent shared knowledge (not needed here) |

---

## Detailed Feature Breakdown

### ✅ ENABLED FEATURES (We're Using)

#### 1. **Chat History** (`ADD_HISTORY_TO_CONTEXT=true`)
- **What:** Includes recent conversation messages in context automatically
- **Config:** `num_history_runs=3` (last 3 turns)
- **Cost:** No extra LLM calls (local database lookup)
- **Pros:** Seamless conversation continuity, context-aware responses
- **Cons:** Increases context size, irrelevant old messages included
- **When:** Always for conversational agents
- **Example:** User asks "what about spicy?", agent remembers previous recipe suggestions

#### 2. **Sessions** (`db=SqliteDb(...)`)
- **What:** Unique `session_id` groups all interactions into conversation threads
- **Cost:** No extra cost (automatic database operation)
- **Pros:** Multi-user support, persistent across restarts, separates conversations
- **Cons:** Requires database setup
- **When:** Multi-turn, multi-user applications
- **Example:** User A has session_1, User B has session_2; no mixing

#### 3. **User Memories** (`ENABLE_USER_MEMORIES=true`)
- **What:** Automatically extracts and stores user preferences
- **Cost:** ✓ **Extra LLM API calls** for extraction (via AGENT_MNGT_MODEL)
- **Pros:** Personalized recommendations, no re-stating preferences
- **Cons:** Privacy considerations, storage overhead
- **When:** Personalized agents, CRM-like systems
- **Stored:** Name, dietary restrictions, cuisine preferences, meal type
- **Example:** "I'm vegetarian" → stored → future recipes skip meat

#### 4. **Session Summaries** (`ENABLE_SESSION_SUMMARIES=false`)
- **What:** Auto-summarizes long conversations to save context tokens
- **Cost:** ✓ **Extra LLM API calls** for compression
- **Config:** Disabled by default (enable for cost optimization)
- **Pros:** Handles long conversations without token bloat
- **Cons:** Summary quality varies, loses nuance
- **When:** Long conversations (100+ turns), token-constrained apps
- **Example:** "User wants healthy, quick, vegetarian recipes" (summary of 50 turns)

#### 5. **Tool Result Compression** (`COMPRESS_TOOL_RESULTS=true`)
- **What:** Reduces verbosity of API responses before adding to context
- **Cost:** No extra LLM calls (uses AGENT_MNGT_MODEL in background)
- **Pros:** Shrinks context, faster responses
- **Cons:** May lose detail
- **When:** Always for API-heavy agents
- **Example:** 2000-char recipe → 500-char summary in context

#### 6. **Multi-Session History** (`SEARCH_SESSION_HISTORY=true`, `NUM_HISTORY_SESSIONS=2`)
- **What:** Can search and retrieve context from past 2 sessions
- **Cost:** No extra LLM calls (local database search)
- **Pros:** Long-term preference tracking, avoids repetition
- **Cons:** Larger context, may be irrelevant
- **When:** Long-term personalization needed
- **Example:** User preferences from yesterday's session used in today's chat

#### 7. **Learning Machines** (`ENABLE_LEARNING=true`, `LEARNING_MODE=AGENTIC`)
- **What:** Comprehensive system for dynamic insight extraction
- **Stores:** User profiles, preferences, learnings, session context
- **Cost:** ✓ **Extra LLM API calls** for extraction
- **Modes:**
  - **ALWAYS:** Automatic extraction (most calls)
  - **AGENTIC:** Agent decides when to save (recommended, what we use)
  - **PROPOSE:** User confirms before saving (high-stakes)
- **Pros:** Evolving agent, learns from experience, improves over time
- **Cons:** Storage, API calls, complexity
- **When:** Long-running, adaptive systems
- **Example:** Agent extracts "user prefers quick recipes", saves to global insights

#### 8. **LearnedKnowledge** (Part of Learning Machines)
- **What:** Agent-created insights stored in vector database
- **Namespace:** `"global"` (shared across all users)
- **Storage:** LanceDB (embedded vector search)
- **Cost:** ✓ **Extra LLM calls** for extraction
- **Pros:** Shared wisdom, no manual curation, evolves naturally
- **Cons:** Quality depends on agent reasoning
- **When:** Multi-tenant systems, shared learning desired
- **Example:** "For seafood + garlic, always add lemon" (learned across users)

#### 9. **Learning Context Injection** (`ADD_LEARNINGS_TO_CONTEXT=false`)
- **What:** Automatically injects learned insights into LLM context
- **Cost:** No extra LLM calls (local operation), but increases context size if enabled
- **Critical Dependency:** LEARNING_MODE selection:
  - **AGENTIC (recommended):** Set to `false`
    - Agent controls learnings via tools (`search_learnings`, `save_learning`)
    - Auto-injection creates redundancy and token bloat
    - Pattern: Same as Agentic RAG (`search_knowledge=true` vs `add_knowledge_to_context=true`)
  - **ALWAYS:** Set to `true`
    - Relies on automatic extraction + context injection workflow
    - Learnings automatically injected via `<relevant_learnings>` tags
  - **PROPOSE:** Set to `true`
    - Learnings need context for user review before saving
- **Default:** `false` (aligns with recommended AGENTIC mode)
- **Pros:** Agent-controlled selective learning, reduces token bloat, efficient retrieval
- **Cons:** Agent must explicitly call `search_learnings` when needed
- **When:** AGENTIC mode (default setup), cost-sensitive applications
- **Example:** Agent searches learnings about "seafood" only when reasoning about seafood recipes

#### 10. **Datetime Context** (`ADD_DATETIME_TO_CONTEXT=true`)
- **What:** Includes current date, time, and timezone in agent context automatically
- **Config:** `timezone_identifier="Etc/UTC"` (supports all TZ Database formats)
- **Cost:** No extra LLM calls (local operation)
- **Pros:** Time-aware recipes, supports temporal queries, seasonal ingredient awareness
- **Cons:** None (lightweight local operation)
- **When:** Always for conversational recipe agents
- **Example:** User asks "What can I cook in 30 minutes?" or "Give me summer recipes" → agent knows current time/season

#### 11. **Location Context** (`ADD_LOCATION_TO_CONTEXT=false`)
- **What:** Includes user location in agent context for geo-aware reasoning
- **Cost:** No extra LLM calls (local operation)
- **Pros:** Local ingredient availability, regional cuisine recommendations, seasonal ingredients by region
- **Cons:** ⚠️ **Privacy consideration** - requires explicit user permission to enable
- **When:** With explicit user consent; consider GDPR/privacy regulations
- **How to Enable:** `ADD_LOCATION_TO_CONTEXT=true` (requires location permission from user)
- **Example:** "What local vegetables are in season?" or "Traditional Tuscan recipes"

#### 12. **Session Caching** (`CACHE_SESSION=false`)
- **What:** Cache agent session in memory for faster subsequent access
- **Cost:** Increased memory usage; may have stale data in distributed systems
- **Pros:** Faster response times for repeated requests in same session
- **Cons:** Not suitable for multi-server deployments (data consistency issues)
- **When:** Single-server deployments with high request volume for same session
- **How to Enable:** `CACHE_SESSION=true` (development/small deployments only)
- **Example:** Same user making multiple consecutive recipe requests

#### 13. **Debug Mode** (`DEBUG_MODE=false`)
- **What:** Enable detailed logging, system message inspection, and debug output
- **Cost:** Slightly slower responses, verbose logs
- **Pros:** Troubleshooting, see compiled system message, understand agent reasoning
- **Cons:** Not suitable for production, verbose output makes logs harder to read
- **When:** Development, debugging, testing system message effectiveness
- **How to Enable:** `DEBUG_MODE=true` (development only)
- **Example:** View full compiled system message including instructions, history, learnings

---

### ⚠️ AVAILABLE BUT NOT REQUIRED

These features are implemented and available but not essential for basic recipe recommendations:
- **Location Context:** Useful for local/regional recipes but requires user permission
- **Session Caching:** Optional performance optimization for single-server setups
- **Debug Mode:** Optional development/troubleshooting feature

---

### ❌ DISABLED/NOT USED

#### **Knowledge Base** (`SEARCH_KNOWLEDGE=false`)
- **What:** External documents ingestion (PDFs, URLs, FAQs)
- **Purpose:** Ground responses in static facts
- **Cost:** No extra LLM calls for search (agent decides when)
- **Why we don't use:** Recipe domain doesn't need static docs; dynamic learnings better
- **When to use:** Documentation Q&A, support systems, legal contracts
- **WARNING:** ⚠️ **Don't use both Knowledge + LearnedKnowledge** - choose one:
  - Use Knowledge for static reference material
  - Use LearnedKnowledge for dynamic insights
  - Using both = redundancy, wasted tokens

#### **Skills** (Not Implemented)
- **What:** Lazy-loaded domain expertise packages (instructions + scripts)
- **Purpose:** Progressive capability discovery, reusable across agents
- **Why we don't use:** Recipe agent is simple; system instructions sufficient
- **Complexity:** Too much for single-domain agent
- **When to use:** Multi-agent systems (code review, debugging, docs)
- **Example:** "Code Review Skill" shared between PR agent, debug agent, etc.

#### **Culture** (Not Implemented)
- **What:** Shared organizational principles for multi-agent systems
- **Purpose:** Consistency across agent teams
- **Why we don't use:** Single agent; no multi-agent coordination needed
- **Complexity:** Designed for 5+ coordinating agents
- **When to use:** Enterprise teams with multiple specialized agents
- **Example:** "Always provide step-by-step solutions" (org-wide principle)

---

## Configuration Summary

Configuration table showing environment variables, defaults, and notes:

| Feature | Environment Variable | Default Value | Notes |
|---------|----------------------|----------------|-------|
| **Chat History** | `ADD_HISTORY_TO_CONTEXT` | `true` | Includes recent messages in context automatically (local operation) |
| **History Depth** | `NUM_HISTORY_RUNS` | `3` | Number of conversation turns to include |
| **Multi-Session Search** | `SEARCH_SESSION_HISTORY` | `true` | Enable cross-session context search (local operation) |
| **Session Count** | `NUM_HISTORY_SESSIONS` | `2` | Number of past sessions to search (keep 2-3 for performance) |
| **User Memories** | `ENABLE_USER_MEMORIES` | `true` | Extract and store user preferences (**extra LLM calls** with AGENT_MNGT_MODEL) |
| **Session Summaries** | `ENABLE_SESSION_SUMMARIES` | `false` | Auto-compress long chats (**extra LLM calls** with AGENT_MNGT_MODEL, disabled by default for cost) |
| **Tool Compression** | `COMPRESS_TOOL_RESULTS` | `true` | Shrink API responses in context (local operation, uses AGENT_MNGT_MODEL) |
| **Learning Machines** | `ENABLE_LEARNING` | `true` | Enable dynamic insight extraction (**extra LLM calls** with AGENT_MNGT_MODEL) |
| **Learning Mode** | `LEARNING_MODE` | `AGENTIC` | How agent learns: `ALWAYS` (auto), `AGENTIC` (agent-controlled, recommended), `PROPOSE` (user-approved) |
| **Learning Context Injection** | `ADD_LEARNINGS_TO_CONTEXT` | `false` | **AGENTIC mode:** false (agent uses tools); **ALWAYS mode:** true (auto-inject learnings) |
| **Datetime Context** | `ADD_DATETIME_TO_CONTEXT` | `true` | Include current date/time for time-aware recipes (local operation) |
| **Timezone** | `TIMEZONE_IDENTIFIER` | `Etc/UTC` | Timezone for datetime context (TZ Database format) |
| **Location Context** | `ADD_LOCATION_TO_CONTEXT` | `false` | Include user location for geo-aware recipes (requires user permission) |
| **Session Caching** | `CACHE_SESSION` | `false` | Cache session in memory (single-server only, not for distributed systems) |
| **Debug Mode** | `DEBUG_MODE` | `false` | Enable detailed logging and system message inspection (development only) |
| **Knowledge Base Search** | `SEARCH_KNOWLEDGE` | `false` | Search external docs (disabled by default - use LearnedKnowledge for dynamic learning instead) |

**Models Used:**
- **Main Model:** `GEMINI_MODEL` (default: `gemini-3-flash-preview`) - Recipe reasoning
- **Agent Management Model:** `AGENT_MNGT_MODEL` (default: `gemini-2.5-flash-lite`) - Used for all features marked with extra LLM calls (98% cheaper than main model)
- **Image Model:** `IMAGE_DETECTION_MODEL` (default: `gemini-2.5-flash-lite`) - Ingredient detection

---

## Cost Analysis

### No Extra LLM Calls Required
✓ Chat history
✓ Sessions
✓ Tool compression
✓ Multi-session history search
✓ Knowledge base search (agent-triggered, optional)

### Extra LLM API Calls
✗ User memories (preference extraction)
✗ Session summaries (compression)
✗ Learning machines (insight extraction)
✗ LearnedKnowledge (saving insights)

**Cost Optimization:** Disable `ENABLE_SESSION_SUMMARIES` if not handling 100+ turn conversations. Use `AGENT_MNGT_MODEL` (gemini-2.5-flash-lite, 98% cheaper) for all background operations.

---

## Decision Matrix: When to Use What

| Scenario | Feature | Config |
|----------|---------|--------|
| User says "remember I'm vegetarian" | User Memories | `ENABLE_USER_MEMORIES=true` |
| Reference "what we talked about yesterday" | Multi-Session History | `SEARCH_SESSION_HISTORY=true` |
| 5-turn conversation → 1-turn summary | Session Summaries | `ENABLE_SESSION_SUMMARIES=true` |
| Save "best pairing: shrimp + garlic" | LearnedKnowledge | `ENABLE_LEARNING=true` + `LEARNING_MODE=AGENTIC` |
| Search company wiki/docs | Knowledge Base | `SEARCH_KNOWLEDGE=true` |
| Reuse "code review steps" across agents | Skills | Not applicable (single agent) |
| Org-wide "always be empathetic" | Culture | Not applicable (single agent) |

---

## Recommended Setup for Different Use Cases

### 📝 Simple Recipe Bot (Our Setup)
```
ADD_HISTORY_TO_CONTEXT=true
ENABLE_USER_MEMORIES=true
ENABLE_LEARNING=true
LEARNING_MODE=AGENTIC
SEARCH_SESSION_HISTORY=true
ENABLE_SESSION_SUMMARIES=false       # Keep cost low
SEARCH_KNOWLEDGE=false               # Not needed
```

### 💼 Support/Help Desk Agent
```
ADD_HISTORY_TO_CONTEXT=true
ENABLE_USER_MEMORIES=true
ENABLE_SESSION_SUMMARIES=true        # Long conversations common
SEARCH_KNOWLEDGE=true                # Search FAQ/docs
ENABLE_LEARNING=false                # Or PROPOSE mode (high-stakes)
```

### 🏢 Enterprise Multi-Agent System
```
ENABLE_LEARNING=true
LEARNING_MODE=ALWAYS
SKILLS=true                          # Reusable domain packages
CULTURE=true                         # Org-wide principles
SEARCH_KNOWLEDGE=true                # Shared docs
```

---

## Troubleshooting

**Problem:** "No knowledge base configured" warnings
**Solution:** Add `knowledge=knowledge` to LearningMachine when `ENABLE_LEARNING=true`

**Problem:** Context too large, slow responses
**Solution:** Disable `SEARCH_SESSION_HISTORY` or lower `NUM_HISTORY_SESSIONS`

**Problem:** API costs too high
**Solution:** Disable `ENABLE_SESSION_SUMMARIES`, reduce `ENABLE_USER_MEMORIES` to `PROPOSE` mode

**Problem:** Agent doesn't remember yesterday's preferences
**Solution:** Enable `SEARCH_SESSION_HISTORY=true` and `ENABLE_LEARNING=true`

---

## Key Takeaways

1. **We use 8/11 Agno features** - very comprehensive setup
2. **4 features require extra LLM calls** - managed via cost-optimized MEMORY_MODEL
3. **LearnedKnowledge > Knowledge for dynamic domains** - choose one, not both
4. **Skills/Culture not needed** - designed for multi-agent scenarios
5. **AGENTIC learning mode** - best balance of autonomy and control
6. **Always enable chat history** - foundation for conversational AI
