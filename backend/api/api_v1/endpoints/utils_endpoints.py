import logging
import mimetypes
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend import config
from backend.api.api_v1.endpoints.artefacts_endpoints import get_artefact
from backend.decorators import log_endpoint
from backend.dependencies import get_db
from backend.utils.extract_text import (extract_docx_text, extract_md_text,
                                        extract_odt_text, extract_pdf_text,
                                        extract_rtf_text, extract_txt_text)

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@router.get("/extract_text_from_file")
@log_endpoint
async def extract_text_from_file(uuid: str, db=Depends(get_db)) -> str:
    """This endpoint will indetify type of file and extract text from it."""
    document = await get_artefact(uuid=uuid, db=db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / document.customer_id / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(file_path.name)
    supported_doc_types = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/rtf',
        'text/rtf',
        'application/x-rtf',
        'text/plain',
        'text/markdown',
        'application/vnd.oasis.opendocument.text'
    }
    supported_image_types = {
        'image/png',
        'image/jpeg',
        'image/webp',
        'image/gif'
    }
    if mime_type in supported_image_types:
        return await extract_text_from_image(uuid, db)
    elif mime_type in supported_doc_types:
        return await extract_text_from_document(uuid, db)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Supported formats: PDF, DOC, DOCX, RTF, TXT, MD, ODT, PNG, JPEG, WEBP, GIF"
        )


@router.get("/document_to_text")
@log_endpoint
async def extract_text_from_document(uuid: str, db=Depends(get_db)) -> str:
    """Convert PDF, DOC, DOCX, TXT, ODT to plaintext."""

    document = await get_artefact(uuid=uuid, db=db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / document.customer_id / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_extension = file_path.suffix.lower()

        if file_extension == '.pdf':
            return extract_pdf_text(file_path)
        elif file_extension == '.docx':
            return extract_docx_text(file_path)
        elif file_extension == '.doc':
            # fallback for legacy .doc files using antiword
            try:
                result = subprocess.run(
                    ['antiword', str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
                return result.stdout.decode('utf-8')
            except subprocess.CalledProcessError as e:
                logger.error(f"Antiword failed to process {file_path}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing legacy .doc file: {str(e)}"
                )
        elif file_extension == '.rtf':
            return extract_rtf_text(file_path)
        elif file_extension == '.txt':
            return extract_txt_text(file_path)
        elif file_extension == '.md':
            return extract_md_text(file_path)
        elif file_extension == '.odt':
            return extract_odt_text(file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Supported formats: PDF, DOC, DOCX, RTF, TXT, MD, ODT"
            )

    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/image_to_text")
@log_endpoint
async def extract_text_from_image(uuid: str, db=Depends(get_db)) -> str:
    """Convert image to plaintext utilising LLM."""

    # XXX TODO utilise LLM to extract text from image
    # XXX TODO LLM should extract metadata as well such as document type and any descriptive info it can produce really and store this as raw_text

    image = await get_artefact(uuid=uuid, db=db)
    if not image:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / image.customer_id / image.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return "XXX TODO"
