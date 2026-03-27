# AgentEvo.io — Claude Code Context

## Project Overview
SaaS platform for AI agents that learn and evolve through every interaction.
- **Tagline:** AI Agents That Learn and Evolve
- **Owner:** Victor
- **Stage:** Early development

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS |
| Auth | NEAR wallet + Bearer token (account_id) |
| Backend API | FastAPI (Python 3.12) + SQLAlchemy async |
| Agent Engine | LangGraph + LangChain |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue | Redis 7 + Celery |
| Package Manager | pnpm + Turborepo (monorepo) |
| Containerization | Docker + Docker Compose |
| Blockchain | NEAR Protocol (evoagent.testnet / evoagent.near) |

## Project Structure

```
AgentEvo-Claude/
├── apps/
│   ├── web/          # Next.js 15 frontend (port 3000)
│   ├── api/          # FastAPI backend (port 8000)
│   └── workers/      # Celery background workers
├── infrastructure/
│   └── docker/
├── docker-compose.yml
├── .env              # Real env vars (never commit)
└── .env.example
```

## Dev Commands

### Start everything (Docker)
```bash
docker compose up --build
```

### Frontend only
```bash
cd apps/web
pnpm dev
```

### Backend only
```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Workers only
```bash
cd apps/workers
celery -A tasks worker --loglevel=info
```

## Services & URLs
| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## Key Conventions
- Python: async/await everywhere in FastAPI, SQLAlchemy async sessions
- TypeScript: strict mode, no `any`
- Components: server components by default, `"use client"` only when needed
- API routes: RESTful, versioned under `/api/v1/`
- Env vars: always via `core/config.py` (Pydantic Settings), never hardcoded

## Current State (as of Mar 26, 2026)
- [x] Monorepo skeleton (Turborepo + pnpm)
- [x] Next.js 15 frontend with NEAR wallet auth
- [x] Dashboard, Workspace, Agents, Chat pages
- [x] NEAR wallet integration (wallet selector)
- [x] FastAPI backend with modules: agents, chat, evolution, workspaces
- [x] Celery workers skeleton
- [x] Docker Compose setup

## Roadmap (what's next)
- [ ] Connect frontend to FastAPI (api-client.ts → real endpoints)
- [ ] Agent CRUD — create/edit/delete agents from UI
- [ ] LangGraph evolution pipeline (core feature)
- [ ] Real-time chat streaming (WebSockets or SSE)
- [ ] PostgreSQL schema + Alembic migrations
- [ ] NEAR smart contract for agent NFTs
- [ ] Agent marketplace
- [ ] Analytics dashboard

## Dostupni Anthropic modeli (za ovaj API ključ)
- `claude-haiku-4-5-20251001` — najbrži, koristi se u chatu
- `claude-sonnet-4-5-20250929` — balans brzine i kvaliteta
- `claude-sonnet-4-6` — najnoviji
- `claude-opus-4-5-20251101` — najmoćniji, najskuplji
- Stari modeli (claude-3-*) **ne rade** sa ovim API ključem

## Strateški kontakti / Poslovne prilike

- **NEAR Labs** — organizacija iza NEAR Protocol (koristimo za wallet auth + agent NFTs)
  - **Kontaktirati kada:** AgentEvo ima aktivne korisnike i NEAR integracija je kompletna
  - Razlog: Gradimo Web3 AI agent platformu na NEAR-u — prirodni ekosistem partner, grant programi, co-marketing



- **LangChain Inc.** — kompanija koja je napravila LangGraph (koristimo u evolution pipeline-u)
  - Osnivač: Harrison Chase
  - Finansiranje: Sequoia + Benchmark, ~$200M valuacija, nije na burzi (no IPO)
  - **Kontaktirati kada:** AgentEvo ima traction — potencijalni partner ili acquirer
  - Razlog: Gradimo inovativan use case na njihovom frameworku, to je vrijednost za njih

## Poznate napomene / TODO (ne zaboraviti)

- **NEAR cookie za middleware:** Kada se korisnik poveže NEAR walletom, mora se postaviti cookie `near_account_id` jer middleware (Edge runtime) ne može čitati localStorage. U `contexts/near-wallet.tsx`, pri uspješnom connect-u dodati:
  ```js
  document.cookie = `near_account_id=${accountId}; path=/; SameSite=Lax`
  ```
  I obrisati cookie pri disconnect-u.

## What NOT to touch
- `.env` — never modify or commit real secrets
- `pnpm-lock.yaml` — only update via `pnpm install`
- NEAR contract IDs: `evoagent.testnet` (testnet), `evoagent.near` (mainnet)

## Victor's Working Style
- Give tasks step by step — Victor executes one step at a time and reports back
- Prefer explicit commands over explanations
- Always show what file was changed and why
