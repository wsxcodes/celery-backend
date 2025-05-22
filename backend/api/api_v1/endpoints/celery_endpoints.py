import logging
from typing import Any, Dict

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException

from backend.core.celery import celery_app
from backend.db.schemas.rabbitmq_schemas import Msg
from backend.decorators import log_endpoint
from workers.analysis_worker import test_retry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/task-result/{task_id}", response_model=Msg)
@log_endpoint
async def get_task_result(task_id: str) -> Msg:
    """Get the result of a Celery task."""
    task = AsyncResult(task_id, app=celery_app)
    if task.state == "SUCCESS":
        return Msg(id=task_id, result=task.result, state=task.state)
    else:
        return Msg(id=task_id, result=task.result if task.result else "No result", state=task.state)


@router.post("/test-celery-retry")
@log_endpoint
async def test_retry_worker():
    task = test_retry.delay()
    return {"status": "Task queued", "task_id": task.id}


@router.post("/ping-ai-analysis-celery", response_model=Dict[str, Any], status_code=201)
@log_endpoint
async def ping_ai_analysis_celery(word: str) -> Dict[str, Any]:
    """Test Celery worker."""
    logger.debug("ping_ai_analysis_celery route")
    try:
        task = celery_app.send_task(
            "backend.workers.ai_analysis.ping_analysis_worker",
            args=[word],
        )
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start Celery worker")

    return {"id": task.id}
