from celery import Celery

app = Celery('evoagent_workers')
app.config_from_object('celeryconfig')
app.autodiscover_tasks(['tasks.agent_tasks'])
