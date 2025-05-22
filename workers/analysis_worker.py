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


@celery_app.task(
    name='backend.workers.ai_analysis.test_retry',
    bind=True,
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=10
)
def test_retry(self):
    raise Exception('Test exception')


@celery_app.task(
    name='backend.workers.ai_analysis.ping_analysis_worker',
    acks_late=True,
    queue='ai-analysis-queue',
    priority=10
)
def ping_analysis_worker(word: str) -> str:
    logger.info("Processing word: %s", word)
    result = f"Processed word: {word}"
    logger.info("Result: %s", result)
    return result


@celery_app.task(
    name='backend.workers.ai_analysis.analyse_document',
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=900,
    priority=10
)
def analyse_document(document_uuid: str) -> None:
    tokens_spent = 0
    ...
