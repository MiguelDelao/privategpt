"""
Document processing utilities for PrivateGPT Legal AI
Handles text extraction from various document formats
"""

import io
from typing import Optional
from pathlib import Path

import PyPDF2
from docx import Document

class DocumentProcessor:
    """Document processing and text extraction"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt']
    
    def extract_text(self, uploaded_file) -> str:
        """Extract text from uploaded file"""
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if file_extension == '.pdf':
            return self._extract_pdf_text(uploaded_file)
        elif file_extension == '.docx':
            return self._extract_docx_text(uploaded_file)
        elif file_extension == '.txt':
            return self._extract_txt_text(uploaded_file)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _extract_pdf_text(self, uploaded_file) -> str:
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            text_content = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    text_content.append(f"--- Page {page_num + 1} ---\n[Error extracting text: {str(e)}]")
            
            return "\n\n".join(text_content)
        
        except Exception as e:
            raise ValueError(f"Error processing PDF: {str(e)}")
    
    def _extract_docx_text(self, uploaded_file) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(io.BytesIO(uploaded_file.read()))
            text_content = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content.append(para.text)
            
            return "\n\n".join(text_content)
        
        except Exception as e:
            raise ValueError(f"Error processing DOCX: {str(e)}")
    
    def _extract_txt_text(self, uploaded_file) -> str:
        """Extract text from TXT file"""
        try:
            # Try UTF-8 first, fallback to other encodings
            try:
                content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode('latin-1')
            
            return content
        
        except Exception as e:
            raise ValueError(f"Error processing TXT: {str(e)}")
    
    def get_document_type(self, filename: str) -> str:
        """Determine document type based on filename patterns"""
        filename_lower = filename.lower()
        
        # Legal document type classification
        if any(word in filename_lower for word in ['contract', 'agreement', 'lease', 'nda']):
            return 'contract'
        elif any(word in filename_lower for word in ['case', 'court', 'ruling', 'decision']):
            return 'case_law'
        elif any(word in filename_lower for word in ['filing', 'motion', 'brief', 'pleading']):
            return 'filing'
        elif any(word in filename_lower for word in ['memo', 'memorandum', 'opinion']):
            return 'memo'
        elif any(word in filename_lower for word in ['statute', 'regulation', 'code']):
            return 'statute'
        else:
            return 'document'
    
    def validate_file(self, uploaded_file) -> tuple[bool, Optional[str]]:
        """Validate uploaded file"""
        # Check file size (max 50MB for MVP)
        max_size = 50 * 1024 * 1024  # 50MB
        if uploaded_file.size > max_size:
            return False, f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        
        # Check file extension
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in self.supported_formats:
            return False, f"Unsupported file format. Supported formats: {', '.join(self.supported_formats)}"
        
        return True, None
    
    def get_file_info(self, uploaded_file) -> dict:
        """Get metadata about uploaded file"""
        return {
            "filename": uploaded_file.name,
            "size": uploaded_file.size,
            "type": uploaded_file.type,
            "extension": Path(uploaded_file.name).suffix.lower(),
            "document_type": self.get_document_type(uploaded_file.name)
        } 