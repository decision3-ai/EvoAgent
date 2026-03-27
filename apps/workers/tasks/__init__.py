from celery import Celery

app = Celery('agentevo_workers')
app.config_from_object('celeryconfig')
app.autodiscover_tasks(['tasks.agent_tasks'])
