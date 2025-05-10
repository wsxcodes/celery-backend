import logging

from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/document-to-text")
@log_endpoint
async def convert_document_to_plaintext() -> str:
    """Convert document to plaintext."""

    return "XXX TODO"


@router.get("/image-to-text")
@log_endpoint
async def extract_text_from_image() -> str:
    """Convert image to plaintext."""

    return "XXX TODO"


@router.get("/document-preview")
@log_endpoint
async def generate_document_preview() -> str:
    """Generate a preview of the document."""

    return "XXX TODO"
