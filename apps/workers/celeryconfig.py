import os
from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://redis:6379/0').replace('/0', '/1')

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

task_routes = {
    'tasks.agent_tasks.evolve_agent': {'queue': 'evolution'},
    'tasks.agent_tasks.compute_fitness': {'queue': 'fitness'},
}

task_queues_max_priority = 10
task_default_priority = 5
