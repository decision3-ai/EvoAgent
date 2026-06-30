# Backend Task Skill

## Before you start
- Read CLAUDE.md fully
- Identify which module is affected: core/, chat/, workspaces/, memory/, evosmart/, evolution/, analytics/
- State the files you will touch and why
- Ask ONE question if anything is unclear

## Rules
- async/await everywhere — no sync DB calls
- Redis: always get_redis() from core/redis.py
- Celery: always dispatch via celery_client from core/celery.py
- Env vars: always via core/config.py, never hardcoded
- No new libraries without Victor's approval
- Max 8 files per task

## When done
- List every file changed
- State if Alembic migration is needed
- State if Docker rebuild is needed
- Do NOT push anything — Victor decides
