from celery import Celery
from app.core.config import settings

# Lightweight Celery client — dispatches tasks by name without importing worker code.
# (Core must not import from Plugin per architecture rules)
celery_client = Celery(broker=settings.REDIS_URL)
