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


@router.get("/chat_completion")
@log_endpoint
async def chat_completion() -> Dict[str, str]:
    """LLM chat completion endpoint."""
    return {
        "status": "LLM",
        "message": "XXX",
    }
