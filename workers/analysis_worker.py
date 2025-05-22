import logging

from celery.exceptions import MaxRetriesExceededError
from celery.signals import task_failure
from celery.utils.log import get_task_logger

from backend.core.celery import celery_app

logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)


# XXX TODO add sentry

@task_failure.connect
def handle_task_failure(**kwargs):
    if isinstance(kwargs['exception'], MaxRetriesExceededError):
        logger.error(f"MaxRetriesExceededError: Maximum retry attempts exceeded for task {kwargs['task_id']}")


@celery_app.task(acks_late=True, queue='ai-notifications-queue', priority=10)
def ping_analysis_worker(word: str) -> str:
    logger.info("Processing word: %s", word)
    result = f"Processed word: {word}"
    logger.info("Result: %s", result)
    return result


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,  # 1-second backoff
    retry_jitter=True,  # Apply jitter for randomness
    max_retries=900,  # Roughly 15 minutes of retries
    priority=10
)
def analyse_document(uuid: str) -> None:
    """
    XXX TODO
    """
    ...
