# evoagent.io

> AI Agents That Learn and Evolve — SaaS platform for building agents that grow smarter through every interaction.

**Current version: V3.5 LIVE**

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM Providers | OpenRouter (DeepSeek, Gemini) + Anthropic (fallback) + Google Gemini (EvoSmart) |
| Cache / Queue | Redis 7 + Celery + Celery Beat |
| Package Manager | pnpm + Turborepo (monorepo) |
| Containerization | Docker + Docker Compose |
| Blockchain | NEAR Protocol (reserved for V4) |

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
│   │       ├── evosmart/     # Gemini direct route (stateless)
│   │       ├── memory/       # mem0 client, retriever, embeddings
│   │       ├── evolution/    # constitutional rules
│   │       └── analytics/    # Event tracking, EvoPoints
│   └── workers/          # Celery background workers
│       └── tasks/
│           └── agent_tasks.py
├── infrastructure/
│   └── docker/           # Dockerfiles per service
├── migrations/           # Alembic migrations
├── docker-compose.yml
└── .env.example
```

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js 22+](https://nodejs.org/) + [pnpm](https://pnpm.io/)
- [Python 3.12+](https://www.python.org/)

### 1. Clone & configure environment

```bash
cp .env.example .env
# Edit .env — required keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
```

### 2. Start all services with Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Local development (without Docker)

**Frontend:**
```bash
cd apps/web
pnpm install
pnpm dev
```

**Backend:**
```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Workers:**
```bash
cd apps/workers
celery -A tasks worker --loglevel=info -Q evolution,fitness,memory,celery
```

**DB migrations:**
```bash
docker exec agentevo_api_1 alembic upgrade head
```

## Core Concepts

### Agent Evolution Loop

```
Create Agent → Interact → Collect Feedback → Compute Fitness → Evolve → Repeat
```

1. **Create** — Define an agent with a base model and system prompt
2. **Interact** — Users chat with the agent; every exchange is stored
3. **Feedback** — Users rate responses (thumbs up/down)
4. **Fitness** — Background worker computes a rolling fitness score
5. **Evolve** — Agent prompt is refined; champion vs challenger A/B testing runs nightly
6. **Memory** — Agent remembers facts, preferences, goals across sessions (pgvector)

## Architecture

### Core vs Plugin separation

- **Core** (`api/`) — user-facing: workspaces, chat, memory, evosmart, evolution
- **Plugin** (`workers/`) — background: fitness scoring, evolution pipeline, memory extraction
- Hard rule: Core never imports from Plugin. Plugin reads Core tables.

### Fallback Chain (chat router)

```
OpenRouter deepseek/deepseek-chat → OpenRouter google/gemini-2.0-flash-001 → Anthropic claude-sonnet-4-6
```

### EvoSmart

Stateless Gemini 2.5 Flash endpoint: `POST /api/v1/evosmart/chat` — no JWT required, history passed by client.

## Nightly Schedule (Celery Beat)

| Time (UTC) | Task |
|---|---|
| 00:00 | `nightly_fitness_beat` — maintenance window starts |
| 01:00 | `clear_maintenance_mode` |
| 02:30 | `decay_memories` — memory decay (skips goals) |
| 03:00 | `evaluate_challenger` — champion vs challenger evaluation |

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for full history and V4 plan.

| Version | Status |
|---|---|
| V1 — Evolution | COMPLETE |
| V2 — Fitness | COMPLETE |
| V2.3 — Champion vs Challenger | COMPLETE |
| V3 — Persistent Memory | COMPLETE |
| V3.5 — EvoSmart + Fallback + EvoPoints + Constitutional | COMPLETE |
| V4 — NEAR wallet auth + smart contracts + multi-agent + Walrus/Sui storage | TBD |

---

Built with by the evoagent.io team.
