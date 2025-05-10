import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image, ImageDraw, ImageFont
import pdf2image
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from odf import text, teletype
from odf.opendocument import load as load_odf
import markdown
from striprtf.striprtf import rtf_to_text

from backend import config
from backend.api.api_v1.endpoints.documents_endpoints import get_document
from backend.decorators import log_endpoint
from backend.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Font for rendering text-based previews (TXT, MD)
try:
    DEFAULT_FONT = ImageFont.truetype("arial.ttf", 12)
except Exception:
    DEFAULT_FONT = ImageFont.load_default()

# Constants
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 1000
MAX_TEXT_LENGTH = 5000  # Limit text to avoid memory issues

def render_text_to_image(text: str) -> Image.Image:
    """Render plain text to an image for TXT and MD files."""
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    y_position = 10
    line_height = 14
    for line in text.split("\n")[:50]:  # Limit to 50 lines
        draw.text((10, y_position), line[:100], font=DEFAULT_FONT, fill="black")  # Limit line length
        y_position += line_height
        if y_position > IMAGE_HEIGHT - line_height:
            break
    return image

def generate_pdf_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for PDF (first page)."""
    try:
        images = pdf2image.convert_from_path(file_path, first_page=1, last_page=1)
        return images[0] if images else None
    except Exception as e:
        logger.error(f"Error generating PDF preview for {file_path}: {str(e)}")
        return None

def generate_docx_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for DOCX (first page text rendered as image)."""
    try:
        doc = Document(file_path)
        text_content = ""
        for para in doc.paragraphs:
            text_content += para.text + "\n"
            if len(text_content) > MAX_TEXT_LENGTH:
                break
        return render_text_to_image(text_content)
    except Exception as e:
        logger.error(f"Error generating DOCX preview for {file_path}: {str(e)}")
        return None

def generate_rtf_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for RTF (extract text using striprtf and render as image)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rtf_content = f.read()
        text_content = rtf_to_text(rtf_content)
        return render_text_to_image(text_content[:MAX_TEXT_LENGTH])
    except Exception as e:
        logger.error(f"Error generating RTF preview for {file_path}: {str(e)}")
        return None

def generate_txt_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for TXT (render text as image)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read(MAX_TEXT_LENGTH)
        return render_text_to_image(text_content)
    except Exception as e:
        logger.error(f"Error generating TXT preview for {file_path}: {str(e)}")
        return None

def generate_md_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for MD (convert to plain text and render as image)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read(MAX_TEXT_LENGTH)
        text_content = markdown.markdown(md_content)
        return render_text_to_image(text_content)
    except Exception as e:
        logger.error(f"Error generating MD preview for {file_path}: {str(e)}")
        return None

def generate_odt_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for ODT (extract text and render as image)."""
    try:
        doc = load_odf(str(file_path))
        text_content = teletype.extractText(doc.text)
        return render_text_to_image(text_content[:MAX_TEXT_LENGTH])
    except Exception as e:
        logger.error(f"Error generating ODT preview for {file_path}: {str(e)}")
        return None

def generate_doc_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for DOC (treat as DOCX for simplicity, may need pywin32 for true DOC)."""
    return generate_docx_preview(file_path)  # Fallback to DOCX handling

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

        if not image:
            raise HTTPException(status_code=500, detail="Failed to generate preview image")

        # Save the image
        image.save(resultant_image_path, "PNG")
        return str(resultant_image_path)

    except Exception as e:
        logger.error(f"Error generating preview for {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")
