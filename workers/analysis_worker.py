import datetime
import json
import logging

from celery.exceptions import MaxRetriesExceededError
from celery.signals import task_failure
from celery.utils.log import get_task_logger

from backend import config
from backend.core.celery import celery_app
from backend.dependencies import ai_client
from backend.utils import prompt_generators
from backend.utils.helpers import get_document, safe_request
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
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=100,
    priority=5
)
def house_clean(document_uuid: str) -> None:
    document = get_document(document_uuid=document_uuid)
    # XXX TODO delete document from the filesystem
    ...


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=1000,
    priority=5
)
def execute_webhook(document_uuid: str) -> None:
    document = get_document(document_uuid=document_uuid)
    webhook_url = document["webhook_url"]
    logger.info(f"Webhook URL: {webhook_url}")
    response = safe_request(
        request_type="POST",
        url=webhook_url,
        data=json.dumps(document),
        headers={"Content-Type": "application/json"},
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")
    
    logger.info("Handing over to house_clean")



@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def mark_off_document_record_cost(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Marking document as processed")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={
            "analysis_status": "processed",
            "analysis_completed_at": datetime.datetime.now().isoformat()
        }
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")
    logger.info("Handing over to execute_webhook")
    execute_webhook.delay(
        document_uuid=document_uuid
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def mark_off_ai_alert(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Marking off AI alert")
    document = get_document(document_uuid=document_uuid)
    ai_alerts_and_actions = document["ai_alerts_and_actions"]

    priority = ['alert', 'action_required', 'reminder', 'insights_available']

    # pick the highest‐priority alert present in the list
    document_ai_alert = next(
        (flag for flag in priority
        if any(item.get('findings_type') == flag for item in ai_alerts_and_actions)),
        None
    )

    # build your payload
    payload = {
        "ai_alerts_and_actions": json.dumps(ai_alerts_and_actions)
    }
    if document_ai_alert:
        payload["ai_alert_status"] = document_ai_alert

    logger.info("Marking document as processed")
    response = safe_request(
        request_type="PATCH",
        url=f"{config.API_URL}/api/v1/artefact/metadata/{document_uuid}",
        data=payload
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to mark_off_document_record_cost")
    mark_off_document_record_cost.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def map_eterny_legacy_schemas(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Mapping existing Eterny.io Document Schemas")
    document = get_document(document_uuid=document_uuid)
    document_raw_text = document["document_raw_text"]
    simple_prompt = prompts["map_existing_eterny.io_schemas"]

    with open("prompts/prompts.json", "r") as f:
        eterny_legacy_schema = f.read()

    document_raw_text += "\n\n schema:\n" + eterny_legacy_schema
    data = run_ai_completition(ai_client=ai_client, prompt=simple_prompt, document_text=document_raw_text, output_language="English")
    legacy_schema_dict = json.loads(data["message"])

    usage = data.get("usage")
    tokens_spent += usage["total_tokens"]

    logger.info("Update Eterny.io legacy schema to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={"ai_eterny_legacy_schema": json.dumps(legacy_schema_dict)},
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to mark_off_ai_alert")
    mark_off_ai_alert.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def generate_alerts_and_actions(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Running alerts and actions prompt")
    document = get_document(document_uuid=document_uuid)
    ai_analysis_mode = document["ai_analysis_mode"]
    document_raw_text = document["document_raw_text"]

    document_extra2 = ""
    if ai_analysis_mode == "detailed":
        document_extra2 = "analysis_criteria = \"{ai_analysis_criteria}\"\nfeatures_and_insights = \"{ai_features_and_insights}\"\n\n"

    features_and_insights = prompts["alerts_and_actions"]
    data = run_ai_completition(
        ai_client=ai_client,
        prompt=features_and_insights,
        document_text=document_raw_text,
        document_extra1=str(datetime.datetime.now().date()),
        document_extra2=document_extra2,
        output_language=output_language
        )

    usage = data.get("usage")
    tokens_spent += usage["total_tokens"]

    ai_alerts_and_actions = data["alerts_and_actions"]

    logger.info("Saving Analysis Features & Insights to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={
            "ai_alerts_and_actions": json.dumps(ai_alerts_and_actions)
        }
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to generate_eterny_legacy_schemas")
    map_eterny_legacy_schemas.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def generrate_features_and_insights(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Running AI analysis features & insights")
    document = get_document(document_uuid=document_uuid)

    ai_analysis_criteria = document["ai_analysis_criteria"]

    features_and_insights = prompts["features_and_insights"]
    data = run_ai_completition(ai_client=ai_client, prompt=features_and_insights, document_extra1=ai_analysis_criteria, output_language=output_language, inject_date=True)
    features_and_insights_dict = data["features_and_insights"]

    usage = data.get("usage")
    tokens_spent += usage["total_tokens"]

    logger.info("Saving Analysis Features & Insights to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={
            "ai_features_and_insights": json.dumps(features_and_insights_dict)
        }
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to generate_alerts_and_actions")
    generate_alerts_and_actions.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def generate_analysis_criteria(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Running AI analysis criteria")
    analysis_criteria = prompts["analysis_criteria"]
    document = get_document(document_uuid=document_uuid)
    document_raw_text = document["document_raw_text"]
    data = run_ai_completition(ai_client=ai_client, prompt=analysis_criteria, document_text=document_raw_text, output_language=output_language)

    usage = data.get("usage")
    tokens_spent += usage["total_tokens"]

    logger.info("Saving analysis criteria to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={
            "ai_analysis_criteria": data["message"]
        }
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to generrate_features_and_insights")
    generrate_features_and_insights.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def generate_smart_summary(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Running AI smart summary")

    document = get_document(document_uuid=document_uuid)
    document_raw_text = document["document_raw_text"]
    smart_summary = prompts["smart_summary"]

    data = run_ai_completition(ai_client=ai_client, prompt=smart_summary, document_text=document_raw_text, output_language=output_language, inject_date=True)

    usage = data.get("usage")
    tokens_spent += usage["total_tokens"]

    ai_is_expired = False
    ai_expires = None
    document_expires_str = data["document_expires"]
    if document_expires_str:
        document_expires = datetime.datetime.fromisoformat(document_expires_str)
        ai_expires = document_expires.isoformat()
        ai_is_expired = data["is_expired"]

    logger.info("Saving smart summary to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={
            "ai_category": data["top_category"],
            "ai_sub_category": data["sub_category"],
            "ai_summary_short": data["summary_short"],
            "ai_summary_long": data["summary_long"],
            "ai_expires": ai_expires,
            "ai_is_expired": ai_is_expired
        }
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Hading over to generate_analysis_criteria")
    generate_analysis_criteria.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent
    )


@celery_app.task(
    acks_late=True,
    queue='ai-analysis-queue',
    autoretry_for=(Exception,),
    retry_backoff=1,
    retry_jitter=True,
    max_retries=10,
    priority=5
)
def extract_text_from_document(document_uuid: str, output_language: str, tokens_spent: int) -> None:
    logger.info("Extracting text from document")
    document_raw_text = safe_request(
        request_type="GET",
        url=config.API_URL + f"/api/v1/utils/extract_text_from_file?uuid={document_uuid}",
        data={},
    )
    document_raw_text = document_raw_text.json()

    logger.info("Saving extracted text to database")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={"document_raw_text": document_raw_text},
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to generate_smart_summary")
    generate_smart_summary.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent,
    )


@celery_app.task(
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
    document = get_document(document_uuid=document_uuid)
    output_language = document["ai_output_language"]

    tokens_spent = 0
    logger.info("Starting analysis")
    response = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
        data={"analysis_status": "processing", "analysis_started_at": datetime.datetime.now().isoformat()},
    )
    if response is None:
        raise Exception(f"API call failed for marking document {document_uuid}")

    logger.info("Handing over to extract_text_from_document")
    extract_text_from_document.delay(
        document_uuid=document_uuid,
        output_language=output_language,
        tokens_spent=tokens_spent,
    )
