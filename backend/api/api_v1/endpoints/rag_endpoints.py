import logging
from typing import Dict

from fastapi import APIRouter, Body, Depends

from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
    logger.info(f"Document found: {document}")
    return {
        "status": "XXX",
        "message": "TODO"
    }
