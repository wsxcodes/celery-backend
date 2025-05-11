import logging
import shutil
from pathlib import Path
from typing import Optional

import markdown
import html
import pdf2image
from docx import Document
from fastapi import APIRouter, Depends, HTTPException
from odf import teletype
from odf.opendocument import load as load_odf
from PIL import Image, ImageDraw, ImageFont
from striprtf.striprtf import rtf_to_text
import subprocess
import tempfile

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


def convert_to_pdf_via_libreoffice(file_path: Path) -> Optional[Path]:
    """Convert document formats to PDF using LibreOffice headless."""
    try:
        output_dir = tempfile.mkdtemp()
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, str(file_path)
        ], check=True)
        pdf_path = Path(output_dir) / (file_path.stem + ".pdf")
        if pdf_path.exists():
            return pdf_path
    except Exception as e:
        logger.error(f"Error converting {file_path} to PDF: {e}")
    return None


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
    """Generate preview for DOCX by converting to PDF then rendering first page."""
    pdf_path = convert_to_pdf_via_libreoffice(file_path)
    if pdf_path:
        return generate_pdf_preview(pdf_path)
    # Fallback to text rendering
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
    """Generate preview for RTF by converting to PDF then rendering first page."""
    pdf_path = convert_to_pdf_via_libreoffice(file_path)
    if pdf_path:
        return generate_pdf_preview(pdf_path)
    # Fallback to text rendering
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rtf_content = f.read()
        text_content = rtf_to_text(rtf_content)
        return render_text_to_image(text_content[:MAX_TEXT_LENGTH])
    except Exception as e:
        logger.error(f"Error generating RTF preview for {file_path}: {str(e)}")
        return None


def generate_txt_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for TXT by converting text to HTML then to PDF via LibreOffice, then rendering first page."""
    try:
        # Read and truncate text
        text = file_path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_LENGTH]
        # Wrap in HTML <pre> for styling
        html_content = "<html><body><pre style='font-family:Courier New; font-size:12pt;'>"
        html_content += html.escape(text)
        html_content += "</pre></body></html>"
        # Write temp HTML
        temp_dir = tempfile.mkdtemp()
        temp_html = Path(temp_dir) / (file_path.stem + ".html")
        temp_html.write_text(html_content, encoding="utf-8")
        # Convert to PDF via LibreOffice
        pdf_path = convert_to_pdf_via_libreoffice(temp_html)
        if pdf_path:
            return generate_pdf_preview(pdf_path)
    except Exception as e:
        logger.error(f"Error generating TXT preview via HTML for {file_path}: {e}")
    # Fallback to plain text image
    try:
        return render_text_to_image(text)
    except Exception as e:
        logger.error(f"Error generating TXT preview for {file_path}: {e}")
        return None


def generate_md_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for MD by converting markdown to styled HTML then to PDF via LibreOffice, then rendering first page."""
    try:
        md_content = file_path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_LENGTH]
        # Convert markdown to HTML with common extensions
        body_html = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])
        # CSS for styling markdown elements
        css = """
        body { font-family: Arial, sans-serif; font-size: 12pt; margin: 1cm; }
        h1 { font-size: 18pt; font-weight: bold; }
        h2 { font-size: 16pt; font-weight: bold; }
        h3 { font-size: 14pt; font-weight: bold; }
        code { font-family: Courier New, monospace; background-color: #f9f9f9; padding: 2px 4px; border-radius: 3px; }
        pre { font-family: Courier New, monospace; background-color: #f9f9f9; padding: 8px; border-radius: 3px; }
        blockquote { border-left: 4px solid #ddd; padding-left: 8px; color: #555; }
        ul, ol { margin-left: 1.5em; }
        table { border-collapse: collapse; width: 100%; }
        table, th, td { border: 1px solid #ccc; }
        th, td { padding: 4px; text-align: left; }
        """
        html_content = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body_html}</body></html>"
        # Write temporary HTML file
        temp_dir = tempfile.mkdtemp()
        temp_html = Path(temp_dir) / (file_path.stem + ".html")
        temp_html.write_text(html_content, encoding="utf-8")
        # Convert to PDF via LibreOffice and render first page
        pdf_path = convert_to_pdf_via_libreoffice(temp_html)
        if pdf_path:
            return generate_pdf_preview(pdf_path)
    except Exception as e:
        logger.error(f"Error generating MD preview via styled HTML for {file_path}: {e}")
    # Fallback to plain text rendering
    try:
        text_content = markdown.markdown(md_content, output_format="plain")
        return render_text_to_image(text_content)
    except Exception as e:
        logger.error(f"Error generating MD preview fallback for {file_path}: {e}")
        return None


def generate_odt_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for ODT by converting to PDF then rendering first page."""
    pdf_path = convert_to_pdf_via_libreoffice(file_path)
    if pdf_path:
        return generate_pdf_preview(pdf_path)
    # Fallback to text rendering
    try:
        doc = load_odf(str(file_path))
        text_content = teletype.extractText(doc.text)
        return render_text_to_image(text_content[:MAX_TEXT_LENGTH])
    except Exception as e:
        logger.error(f"Error generating ODT preview for {file_path}: {str(e)}")
        return None


def generate_doc_preview(file_path: Path) -> Optional[Image.Image]:
    """Generate preview for DOC by converting to PDF then rendering first page."""
    pdf_path = convert_to_pdf_via_libreoffice(file_path)
    if pdf_path:
        return generate_pdf_preview(pdf_path)
    # Fallback to DOCX handling
    return generate_docx_preview(file_path)
