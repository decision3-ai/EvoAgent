# ARCHITECTURE — EvoAgent

## Pravila slojeva

- Core never imports from Plugin. Plugin reads Core tables.
- `workers/` is Plugin layer — `api/` is Core layer.
- Celery client in Core dispatches tasks by name only (`send_task`), no worker code imported.

---

## Nightly Schedule (Celery Beat)

| Time (UTC) | Task | Description |
|------------|------|-------------|
| **00:00** | `nightly_fitness_beat` | Maintenance window starts |
| **01:00** | `clear_maintenance_mode` | End maintenance window |
| **02:30** | `decay_memories` | Memory decay (skips goals) |
| **03:00** | `evaluate_challenger` | Champion vs Challenger evaluation |

---

## Redis ključevi

| Ključ | TTL | Svrha |
|---|---|---|
| `evolution_status:{workspace_id}` | — | Status evolution pipeline-a |
| `session_variant:{session_id}` | 24h | Champion/Challenger varijanta sesije |

---

## AI provider lanac

OpenRouter (deepseek/deepseek-chat → google/gemini-2.0-flash-001) → Anthropic (claude-sonnet-4-6)

EvoSmart: direktno Gemini 2.5 Flash.
Embeddings: OpenAI `text-embedding-3-small`.
