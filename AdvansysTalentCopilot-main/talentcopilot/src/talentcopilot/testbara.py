import os
import glob
import requests
import uuid
import mimetypes
import pdfplumber
import fitz  
import logging
from docx import Document
from PIL import Image
import json
import pytesseract
from typing import Dict, Optional
from pypdf import PdfReader
import re 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# YOUR ORIGINAL FUNCTIONS
# ===============================

def file_type_validator_tool(file_path: str) -> Optional[Dict[str, str]]:
    """
    Validates a single file (PDF, DOC, DOCX, PNG, JPG, TIFF).
    If valid, returns {"path": ..., "type": ...}.
    If invalid, logs the error and returns None.
    
    Args:
        file_path (str): Path to the file to validate
        
    Returns:
        dict or None: File info if valid, None if invalid
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

    # Check if file exists
    if not os.path.exists(file_path):
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        with open(os.path.join(output_dir, "error_classification_report.md"), "a") as f:
            f.write(f"- {file_path}: file not found\n")
        return None

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    logger.info(f"Detected MIME type: {mime_type}")
    
    file_type = supported_mimes.get(mime_type)

    if not file_type:
        error_msg = f"Unsupported format for {file_path}: {mime_type}"
        logger.error(error_msg)
        with open(os.path.join(output_dir, "error_classification_report.md"), "a") as f:
            f.write(f"- {file_path}: unsupported format ({mime_type})\n")
        return None

    # Try to open and validate the file
    try:
        if file_type == "pdf":
            with pdfplumber.open(file_path) as pdf:
                # Check if PDF has pages
                if len(pdf.pages) == 0:
                    raise Exception("PDF has no pages")
        elif file_type in ("doc", "docx"):
            doc = Document(file_path)
            # Try to access document properties
            _ = doc.core_properties.title
        elif file_type == "image":
            img = Image.open(file_path)
            # Verify image can be loaded
            img.verify()
            
        logger.info(f"File validation successful: {file_path} -> {file_type}")
        return {"path": file_path, "type": file_type}

    except Exception as e:
        error_msg = f"corrupted or unreadable - {str(e)}"
        logger.error(f"File validation failed for {file_path}: {error_msg}")
        with open(os.path.join(output_dir, "error_classification_report.md"), "a") as f:
            f.write(f"- {file_path}: {error_msg}\n")
        return None


def pdf_text_extractor_tool(pdf_path: str) -> Dict:
    """
    Extract text from PDF using multiple methods.
    First tries pdfplumber, then falls back to PyMuPDF, then OCR.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        dict: Extraction results with success status, text content, and metadata
    """
    logger.info(f"Starting PDF text extraction for: {pdf_path}")
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(pdf_path):
        error_msg = f"PDF file not found: {pdf_path}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "text": ""}
    
    extracted_text = ""
    method_used = ""
    
    try:
        # Method 1: Try pdfplumber first (best for text-based PDFs)
        logger.info(f"Attempting text extraction from {pdf_path} using pdfplumber...")
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")
            
            if text_parts:
                extracted_text = "\n".join(text_parts)
                method_used = "pdfplumber"
                logger.info(f"Successfully extracted text using pdfplumber: {len(extracted_text)} characters")
    
    except Exception as e:
        logger.warning(f"pdfplumber failed: {str(e)}")
    
    # Method 2: Fallback to PyMuPDF if pdfplumber didn't work well
    if not extracted_text or len(extracted_text.strip()) < 50:
        try:
            logger.info("Trying PyMuPDF as fallback...")
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
            
            doc.close()
            
            if text_parts:
                extracted_text = "\n".join(text_parts)
                method_used = "pymupdf"
                logger.info(f"Successfully extracted text using PyMuPDF: {len(extracted_text)} characters")
                
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {str(e)}")
    
    # Method 3: OCR fallback for image-based PDFs
    if not extracted_text or len(extracted_text.strip()) < 50:
        try:
            logger.info("Attempting OCR extraction...")
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page_num in range(min(doc.page_count, 5)):  # Limit OCR to first 5 pages
                page = doc[page_num]
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                
                # Save temporary image for OCR
                temp_img_path = os.path.join(output_dir, f"temp_page_{page_num}.png")
                with open(temp_img_path, "wb") as f:
                    f.write(img_data)
                
                # Perform OCR
                ocr_text = pytesseract.image_to_string(Image.open(temp_img_path))
                if ocr_text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} (OCR) ---\n{ocr_text}")
                
                # Clean up temp file
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
            
            doc.close()
            
            if text_parts:
                extracted_text = "\n".join(text_parts)
                method_used = "ocr"
                logger.info(f"Successfully extracted text using OCR: {len(extracted_text)} characters")
                
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
    
    # Save extracted text to file
    if extracted_text:
        output_file = os.path.join(output_dir, "pdf_raw_text.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"=== PDF TEXT EXTRACTION ===\n")
            f.write(f"Source: {pdf_path}\n")
            f.write(f"Method: {method_used}\n")
            f.write(f"Characters: {len(extracted_text)}\n")
            f.write(f"=== CONTENT ===\n\n")
            f.write(extracted_text)
        
        logger.info(f"Text saved to {output_file}")
        
        return {
            "success": True,
            "text": extracted_text,
            "method": method_used,
            "output_file": output_file,
            "char_count": len(extracted_text)
        }
    else:
        error_msg = "Failed to extract any readable text from PDF"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "text": ""}


def pdf_error_logger_tool(pdf_path: str, error_message: str) -> Dict:
    """
    Log PDF processing errors to error report.
    
    Args:
        pdf_path (str): Path to the PDF file that had errors
        error_message (str): Description of the error
        
    Returns:
        dict: Logging result status
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    error_file = os.path.join(output_dir, "error_pdf_report.md")
    
    try:
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(f"- {os.path.basename(pdf_path)}: {error_message}\n")
        
        logger.info(f"Error logged for {pdf_path}: {error_message}")
        return {"success": True, "logged": True, "error_file": error_file}
        
    except Exception as e:
        logger.error(f"Failed to log error: {str(e)}")
        return {"success": False, "error": str(e)}


def pdf_validation_tool(pdf_path: str) -> Dict:
    """
    Validate PDF file for common issues before processing.
    
    Args:
        pdf_path (str): Path to the PDF file to validate
        
    Returns:
        dict: Validation results with status and file info
    """
    logger.info(f"Validating PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        return {"valid": False, "error": "File not found"}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            
            if page_count == 0:
                return {"valid": False, "error": "PDF has no pages"}
            
            # Check if PDF is password protected
            if hasattr(pdf, 'is_encrypted') and pdf.is_encrypted:
                return {"valid": False, "error": "PDF is password protected"}
            
            # Try to read first page to check for corruption
            first_page = pdf.pages[0]
            test_text = first_page.extract_text()
            
            file_size = os.path.getsize(pdf_path)
            
            logger.info(f"PDF validation successful: {page_count} pages, {file_size} bytes")
            
            return {
                "valid": True,
                "page_count": page_count,
                "file_size": file_size,
                "has_text": bool(test_text and test_text.strip()),
                "encrypted": False
            }
            
    except Exception as e:
        error_msg = f"PDF validation failed: {str(e)}"
        logger.error(error_msg)
        return {"valid": False, "error": error_msg}

def text_preprocessor_tool(input_file: str, output_file: str = "output/pdf_cleaned_text.txt") -> None:
    """
    Cleans raw CV text from an input file by removing noise, artifacts, and irrelevant formatting,
    and saves the cleaned text to an output file. Does NOT perform sectioning, structuring, or entity
    extraction, as these are handled by another agent. Returns no value.
    
    Args:
        input_file (str): Path to the raw text file (e.g., output/pdf_raw_text.txt).
        output_file (str): Path to save the cleaned text (default: output/pdf_cleaned_text.txt).
        
    Returns:
        None: No return value, as per request.
    """
    logger.info(f"Starting text preprocessing for file: {input_file}")

    def clean_text(text: str) -> str:
        """Remove noise, artifacts, and normalize text formatting."""
        # Remove page numbers (e.g., "Page 1", "1/2", "1 of 2")
        text = re.sub(r'\bPage\s+\d+\b|\b\d+/\d+\b|\b\d+\s+of\s+\d+\b', '', text, flags=re.IGNORECASE)
        
        # Remove headers/footers (common patterns like separator lines or document metadata)
        text = re.sub(r'^-{2,}\n|={2,}\n|\*{2,}\n', '', text)
        text = re.sub(r'\n\s*Curriculum\s+Vitae\s*\n|\n\s*Resume\s*\n', '\n', text, flags=re.IGNORECASE)
        
        # Remove stray symbols, excessive punctuation, and encoding artifacts
        # FIXED: Escape the hyphen or place it at the end to avoid character range interpretation
        text = re.sub(r'[^\w\s.,;:()\-/@&%]', '', text)  # Escaped hyphen with \-
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\n+', '\n', text)  # Normalize newlines
        
        # Standardize casing (sentence case for all content)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # Sentence case: capitalize first letter, lowercase the rest
                cleaned_lines.append(line[0].upper() + line[1:].lower() if len(line) > 1 else line.upper())
        text = '\n'.join(cleaned_lines)
        
        # Standardize date formats (e.g., "Jan 2020" -> "January 2020", "01/01/2020" -> "01-01-2020")
        date_patterns = [
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', r'\1-\2-\3'),  # Normalize 01/01/2020 or 01-01-2020
            (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b', r'\1uary \2')  # Jan 2020 -> January 2020
        ]
        for pattern, replacement in date_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text.strip()

    try:
        # Read raw text from input file
        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            return None

        with open(input_file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Clean the raw text
        cleaned_text = clean_text(raw_text)
        if not cleaned_text:
            logger.error("No valid text after cleaning")
            return None

        # Save to output file
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"=== CLEANED CV TEXT ===\n")
            f.write(f"Source: {input_file}\n")
            f.write(f"Output File: {output_file}\n")
            f.write(f"=== CONTENT ===\n\n")
            f.write(cleaned_text)
        
        logger.info(f"Cleaned text saved to {output_file}")

    except Exception as e:
        logger.error(f"Text preprocessing failed: {str(e)}")
        return None

    return None  # Explicitly return None as requested

# ===============================
# TEST FUNCTION
# ===============================

def run_complete_test(input_path: str):
    """Run the complete PDF processing test flow"""
    
    print("🔍 TESTING COMPLETE PDF PROCESSING FLOW")
    print("=" * 60)
    print(f"Input file: {input_path}")
    print()
    
    # Step 1: File Type Validation
    print("1️⃣ MIME Type & File Validation")
    print("-" * 40)
    
    validation_result = file_type_validator_tool(input_path)
    
    if validation_result is None:
        print("❌ FAILED: File validation failed")
        return False
    
    print(f"✅ SUCCESS: File type = {validation_result['type']}")
    print(f"   Path: {validation_result['path']}")
    print()
    
    # Step 2: PDF Validation
    print("2️⃣ PDF Specific Validation")
    print("-" * 40)
    
    pdf_validation = pdf_validation_tool(input_path)
    
    if not pdf_validation.get('valid', False):
        print(f"❌ FAILED: {pdf_validation.get('error', 'Unknown error')}")
        pdf_error_logger_tool(input_path, pdf_validation.get('error', 'Unknown error'))
        return False
    
    print("✅ SUCCESS: PDF is valid")
    print(f"   Pages: {pdf_validation['page_count']}")
    print(f"   Size: {pdf_validation['file_size']:,} bytes")
    print(f"   Has text: {pdf_validation['has_text']}")
    print()
    
    # Step 3: Text Extraction
    print("3️⃣ Text Extraction")
    print("-" * 40)
    
    extraction_result = pdf_text_extractor_tool(input_path)
    
    if not extraction_result.get('success', False):
        print(f"❌ FAILED: {extraction_result.get('error', 'Unknown error')}")
        pdf_error_logger_tool(input_path, extraction_result.get('error', 'Unknown error'))
        return False
    
    print("✅ SUCCESS: Text extracted")
    print(f"   Method: {extraction_result['method']}")
    print(f"   Characters: {extraction_result['char_count']:,}")
    print(f"   Output file: {extraction_result['output_file']}")
    print()
    
    # Step 4: Show preview of raw text
    print("4️⃣ Raw Text Preview (first 300 chars)")
    print("-" * 40)
    preview = extraction_result['text'][:300].replace('\n', ' ').strip()
    print(f"'{preview}...'")
    print()
    
    # Step 5: Text Preprocessing
    print("5️⃣ Text Preprocessing & Cleaning")
    print("-" * 40)
    
    raw_text_file = extraction_result['output_file']
    cleaned_text_file = "output/pdf_cleaned_text.txt"
    
    try:
        text_preprocessor_tool(raw_text_file, cleaned_text_file)
        
        if os.path.exists(cleaned_text_file):
            print("✅ SUCCESS: Text cleaned and preprocessed")
            print(f"   Input file: {raw_text_file}")
            print(f"   Output file: {cleaned_text_file}")
            
            # Show preview of cleaned text
            with open(cleaned_text_file, "r", encoding="utf-8") as f:
                cleaned_content = f.read()
                # Extract just the content part (after the headers)
                if "=== CONTENT ===" in cleaned_content:
                    content_start = cleaned_content.find("=== CONTENT ===") + len("=== CONTENT ===\n\n")
                    actual_content = cleaned_content[content_start:]
                else:
                    actual_content = cleaned_content
                
                cleaned_preview = actual_content[:300].replace('\n', ' ').strip()
                print(f"   Cleaned preview: '{cleaned_preview}...'")
                print(f"   Cleaned file size: {len(actual_content):,} characters")
        else:
            print("❌ FAILED: Cleaned text file was not created")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Text preprocessing error - {str(e)}")
        return False
    
    print()
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


# ===============================
# MAIN EXECUTION
# ===============================

if __name__ == "__main__":
    # Your PDF path
    input_path = "C:/Users/mohi/Downloads/MostafaMohieAldeinMohammedCV.pdf"
    
    # Check if file exists
    if not os.path.exists(input_path):
        print(f"❌ ERROR: File not found at {input_path}")
        print("Please check the path and try again.")
        exit(1)
    
    # Run the test
    try:
        success = run_complete_test(input_path)
        
        if success:
            print("\n📁 Files created:")
            print("   - output/pdf_raw_text.txt (extracted text)")
            if os.path.exists("output/error_classification_report.md"):
                print("   - output/error_classification_report.md (validation errors)")
            if os.path.exists("output/error_pdf_report.md"):
                print("   - output/error_pdf_report.md (PDF errors)")
        else:
            print("\n❌ Test failed - check error logs in output directory")
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install pdfplumber PyMuPDF python-docx Pillow pytesseract pypdf")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()