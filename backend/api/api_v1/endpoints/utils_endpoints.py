import logging
import mimetypes
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend import config
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db
from backend.utils.extract_text import (extract_docx_text, extract_md_text,
                                        extract_odt_text, extract_pdf_text,
                                        extract_rtf_text, extract_txt_text)
from backend.utils.generate_preview import (generate_doc_preview,
                                            generate_docx_preview,
                                            generate_md_preview,
                                            generate_odt_preview,
                                            generate_pdf_preview,
                                            generate_rtf_preview,
                                            generate_txt_preview)

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
    document = await get_document(uuid=uuid, db=db)
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


@router.get("/image-to-text")
@log_endpoint
async def extract_text_from_image(uuid: str, db=Depends(get_db)) -> str:
    """Convert image to plaintext utilising LLM."""

    # XXX TODO utilise LLM to extract text from image

    # XXX TODO LLM should extract metadata as well such as document type and any descriptive info it can produce really

    image = await get_document(uuid=uuid, db=db)
    if not image:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / image.customer_id / image.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return "XXX TODO"


@router.get("/generate-file-preview")
@log_endpoint
async def generate_file_preview(uuid: str, db=Depends(get_db)) -> str:
    """Generate a preview image of the first page for supported document types."""
    document = await get_document(uuid=uuid, db=db)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(config.BASE_UPLOAD_DIR) / document.customer_id / document.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    preview_dir = Path(config.BASE_UPLOAD_DIR) / document.customer_id / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    resultant_image_path = preview_dir / f"{uuid}.png"

    try:
        file_extension = file_path.suffix.lower()
        image = None

        if file_extension == '.pdf':
            image = generate_pdf_preview(file_path)
        elif file_extension == '.doc':
            image = generate_doc_preview(file_path)
        elif file_extension == '.docx':
            image = generate_docx_preview(file_path)
        elif file_extension == '.rtf':
            image = generate_rtf_preview(file_path)
        elif file_extension == '.txt':
            image = generate_txt_preview(file_path)
        elif file_extension == '.md':
            image = generate_md_preview(file_path)
        elif file_extension == '.odt':
            image = generate_odt_preview(file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Supported formats: PDF, DOC, DOCX, RTF, TXT, MD, ODT"
            )

        # XXX TODO images should be resized to a standard size and recorded in the database

        if not image:
            raise HTTPException(status_code=500, detail="Failed to generate preview image")

        # Save the image
        image.save(resultant_image_path, "PNG")
        return str(resultant_image_path)

    except Exception as e:
        logger.error(f"Error generating preview for {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")
