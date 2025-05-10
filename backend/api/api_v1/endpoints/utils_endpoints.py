import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend import config
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/document-to-text")
@log_endpoint
async def convert_document_to_plaintext(uuid: str, db=Depends(get_db)):
    """Convert document to plaintext."""

    document = await get_document(uuid=uuid, db=db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / document.customer_id / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

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
