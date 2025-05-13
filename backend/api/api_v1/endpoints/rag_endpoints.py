import logging
from typing import Dict

from fastapi import APIRouter, Body, Depends

from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db
from backend.db.schemas.rag_schemas import MessagePayload

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# XXX TODO rag to init conversation about the finding about the documents (alerts, tasks, insights)
# XXX TODO add tasks and alerts in the RAG feature


@router.post("/")
@log_endpoint
async def ask_question_about_document(
    uuid: str,
    question: str = Body(...),
    db=Depends(get_db)
) -> Dict[str, str]:
    """RAG ask endpoint."""
    # XXX tokens_spent should be added to the document metadata
    document = await get_document(uuid, db)

    # XXX TODO rag to init conversation about the finding (alerts, tasks, insights)
    # XXX TODO add tasks and alerts in the RAG feature

    logger.info(f"Document found: {document}")
    return {
        "status": "XXX",
        "message": "TODO"
    }


@router.post("/message")
@log_endpoint
async def record_messages(document_uuid: str, payload: MessagePayload = Body(...), db=Depends(get_db)) -> Dict[str, str]:
    """RAG message endpoint."""

    if payload.question:
        logger.info(f"Message received: question - {payload.question}")
    elif payload.answer:
        logger.info(f"Message received: answer - {payload.answer}")

    return {
        "status": "XXX",
        "message": "TODO"
    }
