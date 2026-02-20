from crewai.tools import tool
import os
import glob
import requests
import uuid
import mimetypes
import pdfplumber
import fitz  
import logging
# from docx import Document
# from PIL import Image
import json
import pytesseract
from typing import Dict, Optional
from pypdf import PdfReader
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool("FileTypeValidatorTool")
def file_type_validator_tool(file_path: str) -> dict:
    """
    Validates a single file (PDF, DOC, DOCX, PNG, JPG, TIFF).
    
    Args:
        file_path (str): Path to the file to validate
        
    Returns:
        dict: File info if valid, error details if invalid
    """
    logger.info(f"Validating file: {file_path}")
    
    supported_mimes = {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "image/png": "image",
        "image/jpeg": "image",
        "image/tiff": "image"
    }

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    error_file = os.path.join(output_dir, "error_classification_report.md")

    # Check file existence
    if not os.path.exists(file_path):
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(f"- {file_path}: {error_msg}\n")
        return {"valid": False, "error": error_msg, "file_path": file_path, "file_type": None}

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    file_type = supported_mimes.get(mime_type)
    
    if not file_type:
        error_msg = f"Unsupported format for {file_path}: {mime_type}"
        logger.error(error_msg)
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(f"- {file_path}: {error_msg}\n")
        return {"valid": False, "error": error_msg, "file_path": file_path, "file_type": None}

    # Validate file integrity
    try:
        if file_type == "pdf":
            with PdfReader(file_path) as pdf:
                if len(pdf.pages) == 0:
                    raise Exception("PDF has no pages")
        elif file_type in ("doc", "docx"):
            from docx import Document
            doc = Document(file_path)
            _ = doc.core_properties.title
        elif file_type == "image":
            from PIL import Image
            img = Image.open(file_path)
            img.verify()
            
        logger.info(f"File validation successful: {file_path} -> {file_type}")
        return {"valid": True, "file_path": file_path, "file_type": file_type, "error": None}
    except Exception as e:
        error_msg = f"Corrupted or unreadable file: {str(e)}"
        logger.error(f"File validation failed for {file_path}: {error_msg}")
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(f"- {file_path}: {error_msg}\n")
        return {"valid": False, "error": error_msg, "file_path": file_path, "file_type": None}

    
    
@tool("PDFTextExtractorTool") 
def pdf_text_extractor_tool(pdf_path: str) -> dict:
    """
    Extract text from PDF using PdfReader.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Extraction results with success status, text content, and metadata
    """
    logger.info(f"Extracting text from PDF: {pdf_path}")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "pdf_raw_text.txt")
    
    try:
        reader = PdfReader(pdf_path)
        extracted_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
        
        if not extracted_text.strip():
            raise Exception("No text extracted from PDF")
        
        # Write extracted text to output file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(extracted_text)
        
        metadata = {
            "tool": "PDFTextExtractorTool",
            "tool_version": "1.0",
            "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page_count": len(reader.pages),
            "word_count": len(extracted_text.split())
        }
        
        logger.info(f"Text extracted successfully from {pdf_path}")
        return {
            "success": True,
            "text": extracted_text,
            "metadata": metadata,
            "file_path": pdf_path
        }
    except Exception as e:
        logger.error(f"Text extraction failed for {pdf_path}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "metadata": {},
            "file_path": pdf_path
        }

@tool("PDFErrorLoggerTool")
def pdf_error_logger_tool(pdf_path: str, error_message: str) -> dict:
    """
    Log PDF processing errors to error report.
    
    Args:
        pdf_path (str): Path to the PDF file
        error_message (str): Description of the error
        
    Returns:
        dict: Logging result status
    """
    logger.info(f"Logging error for {pdf_path}: {error_message}")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    error_file = os.path.join(output_dir, "error_pdf_report.md")
    
    try:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {os.path.basename(pdf_path)}: {error_message}\n")
        logger.info(f"Error logged successfully to {error_file}")
        return {"success": True, "logged": True, "error_file": error_file}
    except Exception as e:
        logger.error(f"Failed to log error for {pdf_path}: {str(e)}")
        return {"success": False, "error": str(e), "logged": False}

@tool("PDFValidationTool")
def pdf_validation_tool(pdf_path: str) -> dict:
    """
    Validate PDF file for common issues before processing.
    
    Args:
        pdf_path (str): Path to the PDF file to validate
        
    Returns:
        dict: Validation results with status and file info
    """
    logger.info(f"Validating PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        return {"valid": False, "error": "File not found", "file_path": pdf_path}
    
    try:
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        
        if page_count == 0:
            logger.error(f"PDF has no pages: {pdf_path}")
            return {"valid": False, "error": "PDF has no pages", "file_path": pdf_path}
        
        # Check if PDF is password protected
        if reader.is_encrypted:
            logger.error(f"PDF is password protected: {pdf_path}")
            return {"valid": False, "error": "PDF is password protected", "file_path": pdf_path}
        
        # Try to read first page to check for corruption
        first_page = reader.pages[0]
        test_text = first_page.extract_text()
        file_size = os.path.getsize(pdf_path)
        
        logger.info(f"PDF validation successful: {pdf_path} ({page_count} pages, {file_size} bytes)")
        return {
            "valid": True,
            "page_count": page_count,
            "file_size": file_size,
            "has_text": bool(test_text and test_text.strip()),
            "encrypted": False,
            "file_path": pdf_path
        }
    except Exception as e:
        logger.error(f"PDF validation failed: {pdf_path} - {str(e)}")
        return {"valid": False, "error": str(e), "file_path": pdf_path}