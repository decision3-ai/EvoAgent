# CHANGELOG — EvoAgent

Završene verzije, od najnovije prema najstarijoj.

---

## V3.5 — EvoSmart + Fallback Chain + EvoPoints + Constitutional ✅

### EvoSmart
- New stateless endpoint: `POST /api/v1/evosmart/chat`
- Direct Gemini 2.5 Flash integration (`google-generativeai`)
- Javni endpoint — bez JWT auth, history passed by client each request
- `GEMINI_API_KEY` env var

### Fallback Chain (chat router)
- Provider chain: OpenRouter (deepseek/deepseek-chat → google/gemini-2.0-flash-001) → Anthropic (claude-sonnet-4-6)
- `OPENROUTER_API_KEY` env var required for OpenRouter providers
- Default agent model changed to `deepseek/deepseek-chat`
- Streaming and non-streaming both use fallback chain

### EvoPoints
- `evo_points` + `evo_points_updated_at` columns on `workspaces`
- +20 on workspace create
- +10 on thumbs up (feedback score=5)
- +3 on code_copy event (deduplicated per message per day)
- Exposed in `WorkspaceResponse` schema

### Constitutional Rules
- `app/evolution/constitutional.py` — `DEFAULT_CONSTITUTIONAL_RULES` + `ANTI_SYCOPHANCY_RULES`
- Injected at end of every system prompt in chat router
- Anti-flattery, anti-sycophancy, directness rules

### Code Quality Fixes (2026-05-08)
- `core/celery.py` — shared Celery client (was duplicated in 2 routers)
- `core/redis.py` — shared Redis connection pool (was open/close per request)
- `workspaces/helpers.py` — `_get_owned_workspace` + `_get_session` extracted from router
- `chat/router.py` — removed duplicate `save_memory` call, fixed payload shadowing
- `workspaces/router.py` — fixed double workspace query in feedback, `datetime.now(UTC)`
- `workers/requirements.txt` + `Dockerfile.workers` — added `pgvector`, `memory` queue

---

## V3 — Persistent Memory ✅

Agents remember context across sessions via Mem0 + pgvector.

- `agent_memories` table (UUID, workspace_id, memory_type, content, importance_score, embedding vector(1536))
- `write_session_memories` Celery task — extracts facts/preferences/goals after each chat turn
- `get_relevant_memories()` — pgvector cosine similarity search, fallback to importance_score ranking
- `decay_memories` Celery beat task at 02:30 UTC (skips memory_type='goal')
- OpenAI `text-embedding-3-small` for multilingual embeddings

---

## V2.3 — Champion vs Challenger ✅

A/B testing for agent prompts.

- `challenger_prompt`, `challenger_started_at`, `active_variant` fields on `agent_profiles`
- 50/50 traffic split per session stored in Redis (TTL 24h): `session_variant:{session_id}`
- Variant injected into analytics event metadata
- `evaluate_challenger` Celery beat task at 03:00 UTC

---

## V2 — Fitness ✅

Background layer: formal scoring, workers, metrics.

- Celery workers + Redis queue
- `fitness_score` on Message (1.0 thumbs up / -1.0 thumbs down)
- Analytics event tracking (`analytics_events` table)
- Maintenance window 00:00–01:00 UTC (`nightly_fitness_beat`, `clear_maintenance_mode`)
- Async evolution pipeline — `run_evolution` fire-and-forget Celery task
- Redis status tracking: `evolution_status:{workspace_id}`

---

## V1 — Evolution ✅

User-facing execution: workspace → chat → plan/code/explain.

- Email/password auth (JWT)
- Workspace CRUD + agent profile settings
- Chat with AI (SSE streaming)
- Session management + smart title generation
- PLAN / CODE / EXPLANATION response format
- Feedback collection (thumbs up/down → DB)
- Code block copy + max-height scroll
- Production deployment (Vercel + VPS)
