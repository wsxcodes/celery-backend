import datetime
import json
import logging
import time

from celery.exceptions import MaxRetriesExceededError
from celery.signals import task_failure
from celery.utils.log import get_task_logger

from backend import config
from backend.core.celery import celery_app
from backend.dependencies import ai_client
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request
from backend.utils.prompt_generators import run_ai_completition

logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)

prompts = prompt_generators.load_prompts()


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
    name='backend.workers.ai_analysis.extract_text_from_document',
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def extract_text_from_document(document_uuid: str, tokens_spent: int) -> None:
    # XXX TODO
    ...


@celery_app.task(
    name='backend.workers.ai_analysis.analyse_document',
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def analyse_document(document_uuid: str) -> None:
    logger.info(f"Document to analyze: {document_uuid}")

    tokens_spent = 0
    logger.info("Starting analysis")
    safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={"analysis_status": "processing", "analysis_started_at": datetime.datetime.now().isoformat()},
    )
