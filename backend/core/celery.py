import os

from celery import Celery
from kombu import Exchange, Queue

from backend import config

# Broker and Backend URLs
default_broker_url = config.RABBITMQ_BROKER
broker_url = os.getenv("RABBITMQ_BROKER", default_broker_url)

default_redis_url = f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/0"
redis_url = os.getenv("REDIS_URL", default_redis_url)

# Initialize Celery
celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=redis_url,
    include=["workers.analysis_worker"]
)

# Celery Configuration
celery_app.conf.update(
    result_expires=86400,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    worker_prefetch_multiplier=4,
    task_soft_time_limit=36000,
    task_time_limit=72000,
    task_create_missing_queues=True,
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    task_default_priority=5,  # Default mid-level priority
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default', durable=True),
        Queue('ai-analysis-queue', Exchange('ai-analysis-exchange'), routing_key='ai-analysis-routing-key', durable=True)
    )
)

# Task Routing
celery_app.conf.task_routes = {
    "workers.analysis_worker.*": {"queue": "ai-analysis-queue"}
}
