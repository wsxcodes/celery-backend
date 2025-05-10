import logging
from pathlib import Path

from docx import Document
from odf import teletype
from odf.opendocument import load
from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        # Extract text using pdfminer.six
        text = extract_text(str(file_path))
        # Clean up the extracted text
        cleaned_text = ' '.join(text.split()).strip()
        return cleaned_text or "No text could be extracted from the PDF"
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        raise


def extract_docx_text(file_path: Path) -> str:
    """Extract text from DOC/DOCX file."""
    try:
        doc = Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        return "\n".join(text).strip() or "No text could be extracted from the document"
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {str(e)}")
        raise


def extract_txt_text(file_path: Path) -> str:
    """Extract text from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            return text.strip() or "No text could be extracted from the text file"
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        with open(file_path, 'r', encoding='latin-1') as file:
            text = file.read()
            return text.strip() or "No text could be extracted from the text file"
    except Exception as e:
        logger.error(f"Error extracting TXT text: {str(e)}")
        raise


def extract_odt_text(file_path: Path) -> str:
    """Extract text from ODT file."""
    try:
        doc = load(file_path)
        text = []
        for element in doc.getElementsByType(text.P):
            extracted_text = teletype.extractText(element)
            if extracted_text.strip():
                text.append(extracted_text)
        return "\n".join(text).strip() or "No text could be extracted from the ODT file"
    except Exception as e:
        logger.error(f"Error extracting ODT text: {str(e)}")
        raise


def extract_rtf_text(file_path: Path) -> str:
    """Extract text from RTF file."""
    try:
        from striprtf.striprtf import rtf_to_text
        with open(file_path, 'r', encoding='utf-8') as file:
            rtf_content = file.read()
            text = rtf_to_text(rtf_content)
            return text.strip() or "No text could be extracted from the RTF file"
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            rtf_content = file.read()
            text = rtf_to_text(rtf_content)
            return text.strip() or "No text could be extracted from the RTF file"
    except Exception as e:
        logger.error(f"Error extracting RTF text: {str(e)}")
        raise


def extract_md_text(file_path: Path) -> str:
    """Extract text from MD (Markdown) file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            return text.strip() or "No text could be extracted from the markdown file"
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            text = file.read()
            return text.strip() or "No text could be extracted from the markdown file"
    except Exception as e:
        logger.error(f"Error extracting MD text: {str(e)}")
        raise
