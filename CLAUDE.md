# AgentEvo.io — Project Context

## What We Are Building

SaaS coding partner platform. One core AI agent per workspace works with the user through chat.

**Tagline:** AI Agents That Learn and Evolve  
**Owner:** Victor  
**Stage:** V1 pre-launch

---

## V1 Scope (IN)

Everything the user directly sees and uses:

```
user → workspace → session → chat
agent → plans, writes code, explains, iterates
everything saved in DB
SSE streaming
settings affect agent behaviour
```

**Features included in V1:**
- NEAR wallet auth (account_id as Bearer token)
- Workspace CRUD + agent profile settings
- Chat with AI (streaming SSE)
- Session management and history
- PLAN / CODE / EXPLANATION response format
- Feedback collection (thumbs up/down) — silent data for V2
- Code block copy, max-height scroll
- Workspace create/edit UI
- Production deployment (Vercel + VPS)

---

## Out of Scope for V1

Do NOT build, refactor toward, or couple with:

- Multi-agent system
- Fitness / evolution engine
- LangGraph orchestration pipeline
- Celery fitness workers
- NEAR smart contracts
- Agent marketplace
- Analytics dashboard
- Clerk auth (not used — NEAR wallet only)

These are **V2 plugin layer** — they plug in later without touching V1 core.

**Rule:** If the user doesn't directly see it → it's not V1 core.

---

## Architecture Decision — Core vs Plugin

### V1 CORE (user-facing execution)
```
Task → Plan → Code → Explanation → Interaction
```
Core modules: `workspaces/`, `chat/`

### V2 PLUGIN LAYER (background, user never sees)
```
Feedback → Fitness → Evolution → Improved agent
```
Plugin modules: `workers/`, `evolution/`

**Hard rule:** Core does not import from Plugin. Plugin reads Core tables. No circular coupling.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Auth | NEAR wallet + Bearer token (account_id) |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue | Redis 7 + Celery (workers only) |
| Package Manager | pnpm + Turborepo (monorepo) |
| Containerization | Docker + Docker Compose |
| Blockchain | NEAR Protocol (evoagent.testnet / evoagent.near) |

---

## Project Structure

```
AgentEvo/
├── apps/
│   ├── web/          # Next.js 15 frontend (port 3000)
│   ├── api/          # FastAPI backend (port 8000)
│   └── workers/      # Celery background workers (V2)
├── infrastructure/
│   └── docker/       # Dockerfiles per service
├── migrations/       # Alembic migrations (inside apps/api/)
├── docker-compose.yml
├── .env              # Real env vars — NEVER commit
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
```

---

## Services & URLs

| Service | Local | Production |
|---|---|---|
| Frontend | http://localhost:3000 | https://agentevo.io |
| Backend API | http://localhost:8000 | https://api.agentevo.io |
| API Docs | http://localhost:8000/docs | https://api.agentevo.io/docs |
| PostgreSQL | localhost:5432 | managed / VPS |
| Redis | localhost:6379 | managed / VPS |

---

## Available Anthropic Models

- `claude-haiku-4-5-20251001` — fastest, used as default
- `claude-sonnet-4-5-20250929` — balanced
- `claude-sonnet-4-6` — latest
- `claude-opus-4-5-20251101` — most powerful, most expensive
- Old `claude-3-*` models **do not work** with this API key

---

## V1 Roadmap — Current Status

### Done ✅
- Auth (NEAR wallet + security re-login flow)
- Workspace CRUD + agent profile settings
- Workspace create/edit UI
- Chat with AI (AgentEvo AI branding, no Claude/Anthropic mention)
- SSE streaming + fallback to sync
- Session management + smart title generation
- PLAN / CODE / EXPLANATION response format
- Code block copy + max-height scroll + "Copy all code"
- Feedback collection (thumbs up/down → DB)
- Alembic migrations
- Input UX polish
- Deployment readiness (Dockerfile prod, standalone output, CORS)

### Remaining for V1 launch
- [ ] Production deployment (Vercel + VPS)
- [ ] End-to-end smoke test on production
- [ ] Agents page → real API (low priority, not blocking)

### V2 — Evolution Plugin Layer
- [ ] Celery fitness worker
- [ ] LangGraph evolution pipeline
- [ ] NEAR smart contracts for agent NFTs
- [ ] Agent marketplace
- [ ] Analytics dashboard

---

## Working Rules

1. **Small tasks only** — one thing at a time, Victor executes and reports back
2. **No large refactors** — if it touches more than ~8 files, split it or reconsider
3. **No scope creep** — V2 features do not enter V1 code
4. **No new libraries** unless strictly necessary
5. **Core stays clean** — workspaces/ and chat/ must not depend on workers/ or evolution/
6. **Always show** what file changed and why

---

## Known Notes / TODOs

- **NEAR cookie for middleware:** On wallet connect, set `near_account_id` cookie (already done in `near-wallet.tsx`). Edge runtime cannot read localStorage.
- **Clerk is NOT used** — only in `.gitignore` as a leftover. Auth is NEAR wallet only.
- **Model default:** All agent profiles default to `claude-haiku-4-5-20251001`. Fallback is hardcoded in `chat/router.py` for old records with invalid models.
- **`--reload` flag removed** from `Dockerfile.api` for production.

---

## Strategic Contacts

- **NEAR Labs** — contact when AgentEvo has active users + NEAR integration complete
- **LangChain Inc.** — contact when AgentEvo has traction (building on their framework)

---

## What NOT to Touch

- `.env` — never modify or commit real secrets
- `pnpm-lock.yaml` — only update via `pnpm install`
- NEAR contract IDs: `evoagent.testnet` (testnet), `evoagent.near` (mainnet)
