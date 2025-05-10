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


@router.get("/llm")
@log_endpoint
async def llm_xxx() -> Dict[str, str]:
    """LLM xxx endpoint."""
    return {
        "status": "LLM",
        "message": "XXX",
    }
