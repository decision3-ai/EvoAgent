# evoagent.io — Project Context

## What We Are Building

SaaS coding partner platform. One core AI agent per workspace works with the user through chat.

**Tagline:** AI Agents That Learn and Evolve
**Owner:** Victor
**Stage:** V3.5 LIVE

### Version ladder (product language)

| Version | Codename | Status | Meaning |
|---------|----------|--------|---------|
| **V1** | **Evolution** | LIVE | Shipped product: workspace → chat → plan/code/explain, SSE, settings, feedback captured. |
| **V2** | **Fitness** | LIVE | Background layer: formal scoring, workers, metrics, pipelines that turn feedback into measurable fitness (Celery, evolution plugin modules). |
| **V2.3** | **Champion vs Challenger** | LIVE | A/B testing for agent prompts—champion prompt vs challenger prompt, 50/50 traffic split, automatic evaluation. |
| **V3** | **Persistent Memory** | LIVE | Agents remember across sessions via Mem0 + pgvector. Memory writer, retriever, decay. |
| **V3.5** | **EvoSmart + Fallback + Constitutional** | LIVE | Gemini direct route, multi-provider fallback chain, EvoPoints, constitutional rules. |
| **V4** | *TBD* | — | Reserved on the roadmap. |

---

## Current Live Features

### V1 — Evolution (user-facing execution)
```
user → workspace → session → chat
agent → plans, writes code, explains, iterates
everything saved in DB
SSE streaming
settings affect agent behaviour
```

**Features:**
- Email/password auth (JWT)
- Workspace CRUD + agent profile settings
- Chat with AI (streaming SSE)
- Session management and history
- PLAN / CODE / EXPLANATION response format
- Feedback collection (thumbs up/down)
- Code block copy, max-height scroll
- Workspace create/edit UI
- Production deployment (Vercel + VPS)

---

### V2.3 — Champion vs Challenger System

A/B testing framework for agent prompt optimization.

**DB fields on `agent_profiles`:**
- `challenger_prompt` — alternative system prompt being tested
- `challenger_started_at` — timestamp when A/B test began
- `active_variant` — which variant is currently serving (champion/challenger)

**Traffic split:**
- 50/50 per session, stored in Redis with 24h TTL
- Key pattern: `session_variant:{session_id}`

**Analytics:**
- Events track `variant` field in `event_metadata`
- Enables comparing thumbs up/down rates per variant

**Celery task:**
- `evaluate_challenger` runs nightly at **03:00 UTC**
- Compares fitness metrics, promotes challenger if it wins

---

### Pre-V3 — Async Evolution Pipeline

Evolution jobs are fire-and-forget via Celery.

- `run_evolution` Celery task
- Redis tracks status: `evolution_status:{workspace_id}` = `queued` | `running` | `done` | `failed`
- Non-blocking for the user

---

### V3 — Persistent Memory (Mem0 + pgvector)

Agents remember context across sessions.

**DB table `agent_memories`:**
```sql
id              UUID PRIMARY KEY
workspace_id    UUID REFERENCES workspaces(id)
memory_type     VARCHAR  -- 'fact', 'preference', 'goal', 'context'
content         TEXT
importance_score FLOAT
embedding       VECTOR(768)   -- pgvector (Ollama nomic-embed-text)
created_at      TIMESTAMP
last_used_at    TIMESTAMP
```

**Memory Writer:**
- `write_session_memories` Celery task — fire-and-forget after each chat turn
- Extracts facts, preferences, goals from conversation

**Memory Retriever:**
- `get_relevant_memories()` — pgvector cosine similarity search
- Fallback to `importance_score` ranking if no embeddings
- Updates `last_used_at` on retrieved rows
- Injected into agent system prompt at chat time

**Memory Decay:**
- `decay_memories` Celery task runs nightly at **02:30 UTC**
- Reduces `importance_score` over time
- Skips `memory_type='goal'` (goals don't decay)

---

### V3.5 — EvoSmart + Fallback Chain + EvoPoints + Constitutional

#### EvoSmart Route
- `POST /api/v1/evosmart/chat` — direct Gemini 2.5 Flash integration
- Stateless: history passed by client each request
- Javni endpoint — bez JWT auth
- Model: `gemini-2.5-flash` via `google-generativeai`
- `GEMINI_API_KEY` env var

#### Fallback Chain (chat router)
- All providers via OpenRouter: `deepseek/deepseek-chat` → `google/gemini-2.0-flash-001` → `anthropic/claude-sonnet-4.6`
- `OPENROUTER_API_KEY` is **hard-required** — chat returns an explicit error if missing
- Works for both sync (`/chat`) and streaming (`/chat/stream`) endpoints
- Default agent model: `deepseek/deepseek-chat`

#### EvoPoints
- `evo_points` + `evo_points_updated_at` columns on `workspaces`
- +20 on workspace create
- +10 on thumbs up (feedback score=5)
- +3 on code_copy event (deduplicated: 1 per message per day)
- Exposed in `WorkspaceResponse` schema

#### Constitutional Rules
- `app/evolution/constitutional.py` — `DEFAULT_CONSTITUTIONAL_RULES` + `ANTI_SYCOPHANCY_RULES`
- Appended to every system prompt after memory injection
- Anti-flattery, anti-sycophancy, directness, uncertainty acknowledgement

---

## Nightly Schedule (Celery Beat)

| Time (UTC) | Task | Description |
|------------|------|-------------|
| **00:00** | `nightly_fitness_beat` | Maintenance window starts, fitness calculations |
| **01:00** | `clear_maintenance_mode` | End maintenance window |
| **02:30** | `decay_memories` | Memory decay (skips goals) |
| **03:00** | `evaluate_challenger` | Champion vs Challenger evaluation |

---

## Architecture — Core vs Plugin

### CORE — User-facing execution
```
Task → Plan → Code → Explanation → Interaction
```
Core modules: `workspaces/`, `chat/`, `memory/`, `evosmart/`, `evolution/`

### PLUGIN LAYER — Background (user never sees)
```
Feedback → Fitness metrics → Evolution → Memory extraction
```
Plugin modules: `workers/`, `analytics/`

**Hard rule:** Core does not import from Plugin. Plugin reads Core tables. No circular coupling.

### Shared Core Utilities
- `core/celery.py` — single `celery_client` instance (dispatches tasks by name only)
- `core/redis.py` — singleton Redis connection pool (`get_redis()`)
- `workspaces/helpers.py` — `_get_owned_workspace()`, `_get_session()` helpers

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Auth | Email/password (JWT) + NEAR wallet (V2) |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | Ollama `nomic-embed-text` (768 dims, via OpenAI-compatible `/v1` endpoint) |
| LLM providers | OpenRouter (DeepSeek, Gemini, Claude — fallback chain + mem0/evolution) + Google Gemini (EvoSmart) |
| Cache / Queue | Redis 7 + Celery + Celery Beat |
| Package Manager | pnpm + Turborepo (monorepo) |
| Containerization | Docker + Docker Compose |
| Blockchain | NEAR Protocol (evoagent.testnet / evoagent.near) |

---

## Project Structure

```
evoagent.io/
├── apps/
│   ├── web/              # Next.js 15 frontend (port 3000)
│   ├── api/              # FastAPI backend (port 8000)
│   │   └── app/
│   │       ├── core/         # config, database, auth, celery, redis
│   │       ├── chat/         # Chat router, SSE streaming, fallback chain
│   │       ├── workspaces/   # Workspace CRUD, agent profiles, helpers
│   │       ├── evosmart/     # Gemini direct route
│   │       ├── memory/       # mem0 client, retriever, embeddings
│   │       ├── evolution/    # constitutional rules
│   │       └── analytics/    # Event tracking, EvoPoints
│   └── workers/          # Celery background workers
│       └── tasks/
│           └── agent_tasks.py  # run_evolution, evaluate_challenger, write_session_memories, decay_memories
├── infrastructure/
│   └── docker/           # Dockerfiles per service
├── migrations/           # Alembic migrations (inside apps/api/)
├── skills/               # Claude Code skill files (backend-task, migration, debug)
├── docker-compose.yml
├── .env                  # Real env vars — NEVER commit
└── .env.example
```

---

## Key Conventions

- Python: async/await everywhere, SQLAlchemy async sessions
- TypeScript: strict mode, no `any`
- Components: server components by default, `"use client"` only when needed
- API routes: RESTful, versioned under `/api/v1/`
- Env vars: always via `core/config.py` (Pydantic Settings), never hardcoded
- DB changes: always via Alembic migration, never `create_all` in production
- Redis: always use `get_redis()` from `core/redis.py` — never open/close per request
- Celery dispatch: always use `celery_client` from `core/celery.py`

---

## Dev Commands

```bash
# All services (Docker)
cd ~/Documents/AgentEvo
docker-compose up -d

# Frontend only
cd apps/web && pnpm dev

# Backend only (local venv)
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Alembic migrations
docker exec agentevo_api_1 alembic upgrade head
docker exec agentevo_api_1 alembic revision --autogenerate -m "description"

# Celery worker (local)
cd apps/workers && celery -A tasks worker --loglevel=info -Q evolution,fitness,memory,celery

# Celery beat (scheduler)
cd apps/workers && celery -A tasks beat --loglevel=info
```

---

## Services & URLs

| Service | Local | Production |
|---|---|---|
| Frontend | http://localhost:3000 | https://evoagent.io |
| Backend API | http://localhost:8000 | https://api.evoagent.io |
| API Docs | http://localhost:8000/docs | https://api.evoagent.io/docs |
| PostgreSQL | localhost:5432 | managed / VPS |
| Redis | localhost:6379 | managed / VPS |

---

## Git & deploy cadence

- **Frontend (`apps/web` and anything that affects the Vercel build):** commit and push to GitHub immediately so Vercel deploys. Do not leave web-only fixes sitting local unless Victor says to wait.
- **Backend (`apps/api`, `apps/workers`, Docker/VPS, nginx):** no automatic push or deploy — Victor decides when and how.

---

## Available Models

**OpenRouter (all LLM calls except EvoSmart):**
- `deepseek/deepseek-chat` — default agent model (cheapest)
- `google/gemini-2.0-flash-001` — second in chain
- `anthropic/claude-sonnet-4.6` — fallback chain last resort
- `anthropic/claude-haiku-4.5` — mem0 fact extraction + evolution pipeline (`EVOLUTION_MODEL`)
- No direct Anthropic API usage — `ANTHROPIC_API_KEY` removed (Claude goes through OpenRouter)

**Ollama (embeddings only):**
- `nomic-embed-text` — 768 dims, `OLLAMA_BASE_URL` (default `http://ollama:11434`)

**Google (EvoSmart route):**
- `gemini-2.5-flash` — direct Gemini API

---

## Roadmap — Current Status

### V1 — Evolution COMPLETE
### V2 — Fitness COMPLETE
### V2.3 — Champion vs Challenger COMPLETE
### V3 — Persistent Memory COMPLETE
### V3.5 — EvoSmart + Fallback Chain + EvoPoints + Constitutional COMPLETE
- EvoSmart Gemini route (`/api/v1/evosmart/chat`)
- Multi-provider fallback chain (OpenRouter → Anthropic)
- EvoPoints (+20 create, +10 thumbs up, +3 code_copy)
- Constitutional rules + anti-sycophancy injected in every chat

### V4 — TBD
- Multi-agent system
- LangGraph orchestration pipeline
- NEAR smart contracts
- Agent marketplace
- Analytics dashboard

---

## Working Rules

1. **Small tasks only** — one thing at a time, Victor executes and reports back
2. **No large refactors** — if it touches more than ~8 files, split it or reconsider
3. **No scope creep** — future version features do not enter current code
4. **No new libraries** unless strictly necessary
5. **Core stays clean** — workspaces/, chat/, memory/ must not depend on workers/
6. **Always show** what file changed and why
7. **Frontend deploy** — follow **Git & deploy cadence**: web changes -> push to GitHub for Vercel; backend -> only when agreed with Victor

---

## Known Notes / TODOs

- **NEAR cookie for middleware:** On wallet connect, set `near_account_id` cookie (already done in `near-wallet.tsx`). Edge runtime cannot read localStorage.
- **Clerk is NOT used** — only in `.gitignore` as a leftover.
- **Default agent model:** `deepseek/deepseek-chat` via OpenRouter. Entire fallback chain goes through OpenRouter (incl. Claude).
- **`--reload` flag removed** from `Dockerfile.api` for production.
- **Memory embeddings:** Ollama `nomic-embed-text` (768 dims) via `OLLAMA_BASE_URL`. Memory needs `OPENROUTER_API_KEY` (mem0 fact extraction) + a running Ollama instance. `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` are no longer used anywhere.
- **EvoSmart is stateless** — no DB session, no user context, history managed by client.
- **Workers queue:** `evolution,fitness,memory,celery` — all four required.

---

## Strategic Contacts

- **NEAR Labs** — contact when evoagent.io has active users + NEAR integration complete
- **LangChain Inc.** — contact when evoagent.io has traction (building on their framework)

---

## What NOT to Touch

- `.env` — never modify or commit real secrets
- `pnpm-lock.yaml` — only update via `pnpm install`
- NEAR contract IDs: `evoagent.testnet` (testnet), `evoagent.near` (mainnet)
- `celerybeat-schedule` — auto-generated by Celery Beat, in `.gitignore`

---

## Agent Instructions (Claude Code CLI)

### Before starting any task:
1. Read this entire CLAUDE.md first
2. Ask Victor ONE clarifying question if the task is ambiguous
3. State which files you will touch before touching them
4. Never touch more than 8 files per task

### Division of labor:
- **Claude CLI** — backend (apps/api/, apps/workers/, migrations, docker)
- **Gemini CLI** — frontend (apps/web/ only)
- When Victor says "frontend task" → output a Gemini CLI prompt, not code directly

### Code style reminders:
- Python: async/await, never sync DB calls
- Always use get_redis(), never raw Redis
- Always dispatch Celery via celery_client
- Never hardcode env vars — use core/config.py

### When task is done:
- List exactly which files changed
- Tell Victor if a migration is needed
- Tell Victor if a frontend redeploy is needed (push to GitHub)
