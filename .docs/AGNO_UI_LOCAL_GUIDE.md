# How to Use Agno's Agent UI Locally

**Research Date:** January 20, 2026  
**Status:** Complete Guide

## Overview

Agno provides **two UI options** for local deployment:

1. **Agent UI** (Recommended for local development) - Modern Next.js chat interface
2. **AgentOS Web Portal** (os.agno.com) - Cloud-hosted control plane

This guide covers how to use **Agent UI locally** without building a custom interface.

---

## Option 1: Agent UI (Recommended - Local Next.js App)

### What is Agent UI?

- **GitHub:** https://github.com/agno-agi/agent-ui
- **Technology:** Next.js + TypeScript + Tailwind CSS
- **Purpose:** Modern chat interface that connects to your local AgentOS
- **Features:**
  - Real-time streaming chat
  - Tool call visualization
  - Reasoning steps display
  - References/sources support
  - Multi-modality (images, video, audio)
  - Runs on your machine at `http://localhost:3000`

### Setup Steps

#### Step 1: Start Your AgentOS Backend

Your current setup is perfect - it already has AgentOS running at `http://localhost:7777`:

```bash
cd /home/javi_rnr/poc/challenge
make dev
# Runs on http://localhost:7777
```

#### Step 2: Install Agent UI

**Automatic (Recommended):**
```bash
npx create-agent-ui@latest
# Follow prompts to set up
```

**Manual:**
```bash
git clone https://github.com/agno-agi/agent-ui.git
cd agent-ui
pnpm install
pnpm dev
# Runs on http://localhost:3000
```

#### Step 3: Connect to Your AgentOS

1. Open `http://localhost:3000` in your browser
2. In the **left sidebar**, look for the **endpoint URL** (default: `http://localhost:7777`)
3. Hover over it and click **edit**
4. Confirm it shows `http://localhost:7777` (your AgentOS backend)
5. Click **Connect**
6. Start chatting!

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Machine                           │
├──────────────────┬──────────────────────┬──────────────────┤
│                  │                      │                  │
│   Agent UI       │     AgentOS          │  Spoonacular     │
│  (Frontend)      │    (Backend)         │   MCP Server     │
│                  │                      │                  │
│ localhost:3000   │  localhost:7777      │  (external API)  │
│                  │                      │                  │
│ • Next.js        │  • FastAPI server    │  • Recipe search │
│ • React UI       │  • Agent logic       │  • API key auth  │
│ • Real-time      │  • AGUI interface    │                  │
│   streaming      │  • SQLite DB         │                  │
│                  │  • Session tracking  │                  │
└──────────────────┴──────────────────────┴──────────────────┘
         │                      ▲                   │
         │ HTTP requests        │ API calls        │
         │ (chat, images)       │ (recipes)        │
         └──────────────────────┴──────────────────┘
```

### Key Configuration

The Agent UI **automatically detects**:
- ✅ AgentOS running at `http://localhost:7777`
- ✅ Your agents and tools
- ✅ Session management
- ✅ Memory and history

**No code changes needed** - it just works!

---

## Option 2: AgentOS Web Portal (Cloud Alternative)

If you prefer NOT to run a local UI frontend:

### What is os.agno.com?

- **URL:** https://os.agno.com
- **Purpose:** Cloud-hosted control plane for AgentOS
- **Features:**
  - Web-based UI (no local setup)
  - Multi-user collaboration
  - Team management
  - Monitoring & tracing
  - Built-in knowledge management

### Setup

1. **Keep your local AgentOS running:**
   ```bash
   make dev  # Runs on http://localhost:7777
   ```

2. **Go to:** https://os.agno.com
3. **Click:** "Add new OS" (top navigation)
4. **Select:** "Local"
5. **Enter:** `http://localhost:7777`
6. **Name it:** (e.g., "Recipe Agent - Dev")
7. **Click:** "Connect"

### Pros vs Cons

**os.agno.com Pros:**
- ✅ No local setup needed
- ✅ Built-in monitoring
- ✅ Cloud features (backups, collaboration)
- ✅ Professional UI

**os.agno.com Cons:**
- ❌ Cloud-dependent
- ❌ Data leaves your machine
- ❌ Internet required

**Agent UI Pros:**
- ✅ Fully local
- ✅ Fast response
- ✅ Data privacy
- ✅ No cloud dependency
- ✅ Works offline (once loaded)

**Agent UI Cons:**
- ❌ Requires Node.js + pnpm setup
- ❌ Small initial setup overhead

---

## Recommended Workflow

### For Development (What You Should Do)

```bash
# Terminal 1: Start AgentOS backend
cd /home/javi_rnr/poc/challenge
make dev

# Terminal 2: Start Agent UI frontend
cd /path/to/agent-ui
pnpm dev

# Then open http://localhost:3000
```

### Current Setup Analysis

Your current `app.py` serves a **custom HTML UI** at `http://localhost:7777`. This works, but:

**Pros:**
- ✅ Single server to run
- ✅ No frontend setup
- ✅ Works immediately

**Cons:**
- ❌ Custom UI (not Agno's official)
- ❌ Limited features vs Agent UI
- ❌ Manual maintenance required
- ❌ Missing professional UI components

---

## Migration Path: From Custom UI to Agent UI

If you want to **switch from your custom UI to Agno's official Agent UI**:

### Step 1: Remove Custom UI Code

Remove these lines from `app.py`:

```python
# DELETE THESE LINES:
ui_dir = Path(__file__).parent / "src" / "ui"
if ui_dir.exists():
    root_routes_to_remove = [route for route in app.router.routes if hasattr(route, 'path') and route.path == '/']
    for route in root_routes_to_remove:
        app.router.routes.remove(route)
    
    @app.get("/")
    async def serve_ui():
        return FileResponse(ui_dir / "index.html")
    
    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
```

### Step 2: Keep Your Backend

Leave everything else - your AgentOS setup is perfect!

```python
# KEEP THIS:
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

agent_os = AgentOS(
    description="Recipe Recommendation Service - Transform ingredient images into recipes",
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app=app, port=config.PORT, reload=False)
```

### Step 3: Install and Run Agent UI

```bash
# In a new directory
npx create-agent-ui@latest

# Follow setup
cd your-agent-ui
pnpm install
pnpm dev
```

### Step 4: Connect

Open `http://localhost:3000` and point to `http://localhost:7777` ✅

---

## Comparison: All Three Options

| Feature | Custom UI (Current) | Agent UI (Recommended) | os.agno.com (Cloud) |
|---------|-------------------|----------------------|-------------------|
| **Setup Time** | ⚡ Minimal | ⚡ 5 minutes | ⚡ 2 minutes |
| **Location** | Local | Local | Cloud |
| **Runs on** | localhost:7777 | localhost:3000 | Web |
| **UI Quality** | Basic | Professional | Professional |
| **Official Support** | ❌ Custom | ✅ Official | ✅ Official |
| **Features** | Limited | Full | Full |
| **Real-time Streaming** | Basic | ✅ Advanced | ✅ Advanced |
| **Tool Visualization** | ❌ | ✅ | ✅ |
| **Reasoning Display** | ❌ | ✅ | ✅ |
| **References/Sources** | ❌ | ✅ | ✅ |
| **Privacy** | ✅ All local | ✅ All local | ⚠️ Cloud |
| **Data Retention** | ✅ Local only | ✅ Local only | ⚠️ Agno servers |
| **Offline Mode** | ✅ Once loaded | ✅ Once loaded | ❌ |
| **Customization** | ✅ Full control | ✅ Next.js repo | ⚠️ Limited |

---

## Quick Decision Matrix

### Choose **Agent UI** if:
- ✅ You want the official Agno experience
- ✅ You need professional UI features
- ✅ You want tool visualization & reasoning
- ✅ You can run Node.js locally
- ✅ You want full privacy (everything local)
- ✅ You plan to customize later

### Choose **Custom UI** (current) if:
- ✅ You want minimal dependencies
- ✅ You don't want to install Node.js
- ✅ You want a single Python process
- ⚠️ You're okay with basic UI

### Choose **os.agno.com** if:
- ✅ You want zero setup
- ✅ You don't mind cloud
- ✅ You want monitoring/analytics
- ✅ You need team collaboration

---

## Implementation: Switch to Agent UI (Recommended)

### Commands to Execute

```bash
# 1. Keep your backend running
cd /home/javi_rnr/poc/challenge
make dev

# 2. In another terminal, set up Agent UI
npx create-agent-ui@latest
# Select TypeScript: Yes
# Select destination: agent-ui (or your choice)

cd agent-ui
pnpm install

# 3. Update .env.local if needed
# NEXT_PUBLIC_AGENTMOST_URL=http://localhost:7777
# (Usually auto-detected)

# 4. Start the UI
pnpm dev

# 5. Open http://localhost:3000
# Connection should be automatic!
```

### That's it! 🎉

You now have:
- ✅ Professional chat interface
- ✅ Real-time streaming
- ✅ Tool visualization
- ✅ Image support
- ✅ Reasoning display
- ✅ Full local control

---

## References

- **Agent UI GitHub:** https://github.com/agno-agi/agent-ui
- **Agno Docs - Agent UI:** https://docs.agno.com/basics/agent-ui/overview
- **AgentOS Setup:** https://docs.agno.com/agent-os/introduction
- **Agno Framework:** https://github.com/agno-agi/agno

---

## Troubleshooting

### Agent UI can't connect to AgentOS

1. **Check AgentOS is running:**
   ```bash
   curl http://localhost:7777/health
   ```
   Should return: `{"status":"ok"}`

2. **Check Agent UI endpoint:**
   - Open http://localhost:3000
   - Look at left sidebar
   - Verify endpoint shows `http://localhost:7777`

3. **Check firewall:**
   - Both services must be accessible on localhost

### Still seeing JSON API response?

- You're viewing AgentOS directly (port 7777)
- Use Agent UI instead (port 3000)
- Or use os.agno.com portal

---

## Recommendation

**For your project, use Agent UI because:**

1. ✅ Official Agno solution
2. ✅ Professional features built-in
3. ✅ No maintenance burden
4. ✅ Full image/streaming support
5. ✅ Actively maintained
6. ✅ Community support

Your backend (`AgentOS`) is already perfect - just add the frontend!

