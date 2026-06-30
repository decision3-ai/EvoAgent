# Debug Skill

## Before debugging
- Ask Victor: what is the exact error message or unexpected behavior?
- Ask Victor: when did it start happening?
- Never guess — read the actual logs first

## Where to find logs
- API: docker logs agentevo_api_1 --tail=50
- Workers: docker logs agentevo_workers_1 --tail=50
- All services: docker-compose logs --tail=30

## Debug order
1. Read the error — find the exact line and file
2. Check if it's a missing env var (core/config.py)
3. Check if it's a DB/migration issue (alembic current)
4. Check if it's a Redis/Celery connection issue
5. Only then touch code

## Rules
- Fix the root cause, not the symptom
- One fix at a time — confirm it works before moving to the next
- Do not add permanent print/debug statements to production code
- Do not restart containers as a first response — read logs first
- If the bug is in a Celery task, check the workers container, not the API container

## When done
- State what the root cause was
- List every file changed
- State if a migration or Docker rebuild is needed
- Do NOT push anything — Victor decides
