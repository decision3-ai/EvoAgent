# evoagent.io

> AI Agents That Learn and Evolve — SaaS platform for building agents that grow smarter through every interaction.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Agent Engine | LangGraph + LangChain |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue | Redis 7 + Celery |
| Package Manager | pnpm + Turborepo (monorepo) |
| Containerization | Docker + Docker Compose |

## Project Structure

```
evoagent/
├── apps/
│   ├── web/          # Next.js frontend
│   ├── api/          # FastAPI backend
│   └── workers/      # Celery background workers
├── packages/
│   ├── ui/           # Shared React components (future)
│   ├── types/        # Shared TypeScript types (future)
│   └── config/       # Shared ESLint/TS configs (future)
├── infrastructure/
│   └── docker/       # Dockerfiles per service
├── docs/             # Architecture Decision Records
├── .github/
│   └── workflows/    # CI/CD pipelines
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
# Edit .env with your API keys (OpenAI, Anthropic)
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
celery -A tasks worker --loglevel=info
```

## Core Concepts

### Agent Evolution Loop

```
Create Agent → Interact → Collect Feedback → Compute Fitness → Evolve → Repeat
```

1. **Create** — Define an agent with a base model and system prompt
2. **Interact** — Users chat with the agent; every exchange is stored
3. **Feedback** — Users rate responses (thumbs up/down or 1–5 score)
4. **Fitness** — Background worker computes a rolling fitness score
5. **Evolve** — LangGraph pipeline refines the agent's prompt and behavior
6. **Generation** — Each successful evolution increments the agent's `generation` counter

## Environment Variables

See `.env.example` for all required variables.

## Roadmap

- [x] Project skeleton & monorepo setup
- [x] Authentication (NEAR wallet + Bearer token)
- [ ] Agent CRUD UI
- [ ] LangGraph evolution pipeline
- [ ] Real-time interaction streaming (WebSockets)
- [ ] Agent marketplace
- [ ] Multi-agent orchestration
- [ ] Analytics dashboard

---

Built with ❤️ by the evoagent.io team.
