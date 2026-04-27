import os
from celery.schedules import crontab

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

broker_url = REDIS_URL
result_backend = REDIS_URL.replace('/0', '/1')

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

task_routes = {
    'tasks.agent_tasks.evolve_agent': {'queue': 'evolution'},
    'tasks.agent_tasks.compute_fitness': {'queue': 'fitness'},
    'tasks.agent_tasks.check_evolution_triggers': {'queue': 'fitness'},
    'tasks.agent_tasks.nightly_fitness_beat': {'queue': 'fitness'},
    'tasks.agent_tasks.clear_maintenance_mode': {'queue': 'fitness'},
}

task_queues_max_priority = 10
task_default_priority = 5

# Celery Beat schedule
beat_schedule = {
    'nightly-fitness-beat': {
        'task': 'tasks.agent_tasks.nightly_fitness_beat',
        'schedule': crontab(hour=0, minute=0),  # 00:00 UTC — triggers maintenance + fitness
    },
    'clear-maintenance-beat': {
        'task': 'tasks.agent_tasks.clear_maintenance_mode',
        'schedule': crontab(hour=1, minute=0),  # 01:00 UTC — clears maintenance flags
    },
}
