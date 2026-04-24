import os
from typing import Optional
from PyPDF2 import PdfReader
from docx import Document
import io
from app.utils.text_cleaner import clean_text


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from a PDF or DOCX file content.
    
    Args:
        file_content: The binary content of the file.
        filename: The original filename to determine the extension.
        
    Returns:
        The extracted text as a string.
        
    Raises:
        ValueError: If the file type is unsupported.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".pdf":
        text = extract_text_from_pdf(file_content)
    elif ext in [".docx", ".doc"]: # We try parsing .doc with python-docx, though it officially only supports .docx. 
        text = extract_text_from_docx(file_content)
    elif ext == ".txt":
        text = file_content.decode('utf-8')
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    
    return clean_text(text)



def extract_text_from_pdf(file_content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF file: {str(e)}")


def extract_text_from_docx(file_content: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_content))
        text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text.strip())
        return "\n".join(text)
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX file: {str(e)}")
