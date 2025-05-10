import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend import config
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db
from backend.utils.extract_text import (extract_docx_text, extract_odt_text,
                                        extract_pdf_text, extract_txt_text)

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/extract-text-from-file")
@log_endpoint
async def extract_text_from_file(uuid: str, db=Depends(get_db)) -> str:
    """This endpoint will indetify type of file and extract text from it."""
    return "XXX TODO"


@router.get("/document-to-text")
@log_endpoint
async def extract_text_from_document(uuid: str, db=Depends(get_db)) -> str:
    """Convert PDF, DOC, DOCX, TXT, ODT to plaintext."""

    document = await get_document(uuid=uuid, db=db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / document.customer_id / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_extension = file_path.suffix.lower()

        if file_extension == '.pdf':
            return extract_pdf_text(file_path)
        elif file_extension in ('.doc', '.docx'):
            return extract_docx_text(file_path)
        elif file_extension == '.txt':
            return extract_txt_text(file_path)
        elif file_extension == '.odt':
            return extract_odt_text(file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Supported formats: PDF, DOC, DOCX, TXT, ODT"
            )

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/image-to-text")
@log_endpoint
async def extract_text_from_image(uuid: str, db=Depends(get_db)) -> str:
    """Convert image to plaintext."""

    image = await get_document(uuid=uuid, db=db)
    if not image:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / image.customer_id / image.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return "XXX TODO"


@router.get("/generate-file-preview")
@log_endpoint
async def generate_file_preview() -> str:
    """Generate a preview of the document."""

    return "XXX TODO"
