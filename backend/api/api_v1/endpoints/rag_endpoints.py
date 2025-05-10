import logging
from typing import Dict

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/xxx")
@log_endpoint
async def rag_xxx() -> Dict[str, str]:
    """RAG xxx endpoint."""
    return {
        "status": "XXX",
        "message": "TODO",
    }
