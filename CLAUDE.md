# evoagent.io — Project Context

## What We Are Building

SaaS coding partner platform. One core AI agent per workspace works with the user through chat.

**Tagline:** AI Agents That Learn and Evolve
**Owner:** Victor
**Stage:** V3 LIVE

### Version ladder (product language)

| Version | Codename | Status | Meaning |
|---------|----------|--------|---------|
| **V1** | **Evolution** | LIVE | Shipped product: workspace → chat → plan/code/explain, SSE, settings, feedback captured. Evolution here means the agent improves through **conversation and context** with the user. |
| **V2** | **Fitness** | LIVE | Background layer: formal scoring, workers, metrics, pipelines that turn feedback into measurable fitness (Celery, evolution plugin modules). |
| **V2.3** | **Champion vs Challenger** | LIVE | A/B testing for agent prompts—champion prompt vs challenger prompt, 50/50 traffic split, automatic evaluation. |
| **V3** | **Persistent Memory** | LIVE | Agents remember across sessions via Mem0 + pgvector. Memory writer, retriever, decay. |
| **V3.5** | **Constitutional** | NEXT | Constitutional Rules + Anti-sycophancy + EvoPoints gamification. |
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
- Key pattern: `variant:{session_id}`

**Analytics:**
- Events track `variant` field in `event_metadata`
- Enables comparing thumbs up/down rates per variant

**Celery task:**
- `evaluate_challenger` runs nightly at **03:00 UTC**
- Compares fitness metrics, promotes challenger if it wins

---

### Pre-V3 — Async Evolution Pipeline

Evolution jobs are now fire-and-forget via Celery.

**How it works:**
- `evolve_agent` is now `run_evolution` Celery task
- Redis tracks status: `evolution_status:{workspace_id}` = `queued` | `running` | `done` | `failed`
- Non-blocking for the user—evolution happens in background

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
embedding       VECTOR(1536)  -- pgvector
created_at      TIMESTAMP
last_used_at    TIMESTAMP
```

**Memory Writer:**
- `write_session_memories` Celery task runs after each session ends
- Extracts facts, preferences, goals from conversation

**Memory Retriever:**
- `get_relevant_memories()` function
- pgvector cosine similarity search
- Multilingual embeddings via OpenAI `text-embedding-3-small`
- Injected into agent context at chat time

**Memory Decay:**
- `decay_memories` Celery task runs nightly at **02:30 UTC**
- Reduces `importance_score` over time
- Skips `memory_type='goal'` (goals don't decay)

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
Core modules: `workspaces/`, `chat/`, `memory/`

### PLUGIN LAYER — Background (user never sees)
```
Feedback → Fitness metrics → Evolution → Memory extraction
```
Plugin modules: `workers/`, `analytics/`

**Hard rule:** Core does not import from Plugin. Plugin reads Core tables. No circular coupling.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Auth | Email/password (JWT) + NEAR wallet (V2) |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | OpenAI `text-embedding-3-small` |
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
│   │       ├── chat/     # Chat router, SSE streaming
│   │       ├── workspaces/  # Workspace CRUD, agent profiles
│   │       ├── memory/   # Memory writer, retriever, decay
│   │       └── analytics/   # Event tracking, metrics
│   └── workers/          # Celery background workers
│       └── tasks/
│           └── agent_tasks.py  # run_evolution, evaluate_challenger, etc.
├── infrastructure/
│   └── docker/           # Dockerfiles per service
├── migrations/           # Alembic migrations (inside apps/api/)
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

---

## Dev Commands

```bash
# All services (Docker)
cd ~/Documents/evoagent.io
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
cd apps/workers && celery -A tasks worker --loglevel=info

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

- **Frontend (`apps/web` and anything that affects the Vercel build** — e.g. `pnpm-lock.yaml` when web deps change, `apps/web/vercel.json`, shared turbo config if the web build needs it): when a task changes these, **commit and push to GitHub immediately** after the change so **Vercel** can run a new deployment. Do not leave web-only fixes sitting local unless Victor says to wait.
- **Backend (`apps/api`, `apps/workers`, Docker/VPS, nginx):** **no automatic push or deploy**—Victor decides when and how (Git push, rsync, `docker-compose`, migrations, etc.).

---

## Available Anthropic Models

- `claude-haiku-4-5-20251001` — fastest, used as default
- `claude-sonnet-4-5-20250929` — balanced
- `claude-sonnet-4-6` — latest
- `claude-opus-4-5-20251101` — most powerful, most expensive
- Old `claude-3-*` models **do not work** with this API key

---

## Roadmap — Current Status

### V1 — Evolution COMPLETE
- Auth (email/password JWT + parallel NEAR wallet support)
- Workspace CRUD + agent profile settings
- Chat with AI (evoagent.io AI branding)
- SSE streaming + fallback to sync
- Session management + smart title generation
- PLAN / CODE / EXPLANATION response format
- Feedback collection (thumbs up/down -> DB)
- Code block copy + max-height scroll + "Copy all code"
- Alembic migrations
- Production deployment (Vercel + VPS)

### V2 — Fitness COMPLETE
- Celery workers for background jobs
- Fitness scoring pipeline
- Analytics event tracking
- Maintenance window (00:00-01:00 UTC)

### V2.3 — Champion vs Challenger COMPLETE
- A/B testing for agent prompts
- 50/50 traffic split per session (Redis TTL 24h)
- `evaluate_challenger` nightly task at 03:00 UTC
- Variant tracking in analytics events

### V3 — Persistent Memory COMPLETE
- `agent_memories` table with pgvector embeddings
- `write_session_memories` Celery task
- `get_relevant_memories()` cosine similarity retrieval
- `decay_memories` nightly task at 02:30 UTC

### V3.5 — Constitutional NEXT
- [ ] Constitutional Rules for agent behaviour
- [ ] Anti-sycophancy measures
- [ ] EvoPoints gamification system

### Future (V4+)
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
- **Clerk is NOT used** — only in `.gitignore` as a leftover. Auth is NEAR wallet only.
- **Model default:** All agent profiles default to `claude-haiku-4-5-20251001`. Fallback is hardcoded in `chat/router.py` for old records with invalid models.
- **`--reload` flag removed** from `Dockerfile.api` for production.
- **Memory embeddings:** Using OpenAI `text-embedding-3-small` for multilingual support.

---

## Strategic Contacts

- **NEAR Labs** — contact when evoagent.io has active users + NEAR integration complete
- **LangChain Inc.** — contact when evoagent.io has traction (building on their framework)

---

## What NOT to Touch

- `.env` — never modify or commit real secrets
- `pnpm-lock.yaml` — only update via `pnpm install`
- NEAR contract IDs: `evoagent.testnet` (testnet), `evoagent.near` (mainnet)
- `celerybeat-schedule` — auto-generated by Celery Beat
