"""
Document Text Extraction and Chunking Service
Multi-format support with intelligent text segmentation
"""

import logging
from typing import List, Dict, Any
import re
from io import BytesIO
import uuid
import io

# Document processing libraries
try:
    import PyPDF2
    from docx import Document
    import fitz  # PyMuPDF
    import pdfplumber
except ImportError:
    # Installed via requirements.txt
    pass

logger = logging.getLogger(__name__)

class ChunkingService:
    """Extract text from documents and create intelligent chunks"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(f"ChunkingService: chunk_size={chunk_size}, overlap={chunk_overlap}")

    async def extract_text_from_file(self, file_content: bytes, content_type: str, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            filename_lower = filename.lower()
            
            # Route to appropriate extractor
            if filename_lower.endswith('.pdf') or 'pdf' in content_type.lower():
                return await self._extract_pdf(file_content, filename)
            elif filename_lower.endswith('.docx') or 'wordprocessingml' in content_type.lower():
                return await self._extract_docx(file_content)
            elif filename_lower.endswith(('.txt', '.text')) or 'text' in content_type.lower():
                return await self._extract_text(file_content)
            else:
                # Auto-detect based on file header
                if file_content.startswith(b'%PDF'):
                    return await self._extract_pdf(file_content, filename)
                elif file_content.startswith(b'PK\x03\x04'):  # ZIP format (DOCX)
                    return await self._extract_docx(file_content)
                else:
                    # Fallback to text
                    return await self._extract_text(file_content)
                    
        except Exception as e:
            logger.error(f"Text extraction failed for {filename}: {e}")
            raise

    async def _extract_pdf(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF using multiple strategies"""
        
        # Strategy 1: PyMuPDF (best for most PDFs)
        try:
            logger.info(f"Extracting PDF with PyMuPDF: {filename}")
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract regular text
                page_text = page.get_text("text")
                
                # Extract tables
                tables = page.find_tables()
                table_text = ""
                for table in tables:
                    try:
                        table_data = table.extract()
                        for row in table_data:
                            if row:  # Skip empty rows
                                table_text += " | ".join(str(cell) if cell else "" for cell in row) + "\\n"
                        table_text += "\\n"
                    except:
                        continue
                
                # Combine text and tables
                combined_text = page_text
                if table_text.strip():
                    combined_text += f"\\n\\n--- Tables on Page {page_num + 1} ---\\n{table_text}"
                
                if combined_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\\n{combined_text}")
            
            doc.close()
            
            if text_parts:
                full_text = "\\n\\n".join(text_parts)
                logger.info(f"PyMuPDF extracted {len(full_text)} characters from {filename}")
                return full_text
                
        except Exception as e:
            logger.warning(f"PyMuPDF failed for {filename}: {e}, trying pdfplumber")
        
        # Strategy 2: pdfplumber (excellent for tables)
        try:
            logger.info(f"Extracting PDF with pdfplumber: {filename}")
            
            text_parts = []
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = ""
                    
                    # Extract text
                    text = page.extract_text()
                    if text:
                        page_text += text
                    
                    # Extract tables with formatting
                    tables = page.extract_tables()
                    if tables:
                        page_text += f"\\n\\n--- Tables on Page {page_num + 1} ---\\n"
                        for table in tables:
                            for row in table:
                                if row:
                                    page_text += " | ".join(str(cell) if cell else "" for cell in row) + "\\n"
                            page_text += "\\n"
                    
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\\n{page_text}")
            
            if text_parts:
                full_text = "\\n\\n".join(text_parts)
                logger.info(f"pdfplumber extracted {len(full_text)} characters from {filename}")
                return full_text
                
        except Exception as e:
            logger.warning(f"pdfplumber failed for {filename}: {e}, falling back to PyPDF2")
        
        # Strategy 3: PyPDF2 (fallback)
        try:
            logger.info(f"Extracting PDF with PyPDF2 fallback: {filename}")
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\\n{page_text}")
                except Exception as e:
                    text_parts.append(f"--- Page {page_num + 1} ---\\n[Error extracting text: {str(e)}]")
            
            full_text = "\\n\\n".join(text_parts)
            logger.info(f"PyPDF2 fallback extracted {len(full_text)} characters")
            return full_text
        
        except Exception as e:
            logger.error(f"All PDF extraction methods failed for {filename}: {e}")
            raise
    
    async def _extract_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = BytesIO(file_content)
            doc = Document(docx_file)
            
            text_parts = []
            
            # Extract paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            full_text = "\\n\\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from DOCX")
            return full_text
            
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise
    
    async def _extract_text(self, file_content: bytes) -> str:
        """Extract text from plain text file with encoding detection"""
        try:
            # Try common encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'ascii']
            
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    logger.info(f"Decoded text file using {encoding}")
                    return text
                except UnicodeDecodeError:
                    continue
            
            # Fallback with error replacement
            text = file_content.decode('utf-8', errors='replace')
            logger.warning("Used UTF-8 with error replacement")
            return text
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    async def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with smart boundaries"""
        if not text.strip():
            return []
        
        try:
            # Clean and normalize text
            text = self._clean_text(text)
            
            # Split into sentences for better boundaries
            sentences = self._split_sentences(text)
            
            chunks = []
            current_chunk = ""
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                # Check if adding sentence would exceed chunk size
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_data = {
                        "content": current_chunk.strip(),
                        "metadata": metadata or {},
                        "length": len(current_chunk.strip())
                    }
                    chunks.append(chunk_data)
                    
                    # Start new chunk with overlap
                    if self.chunk_overlap > 0:
                        overlap_text = self._get_overlap(current_chunk, self.chunk_overlap)
                        current_chunk = overlap_text + " " + sentence
                        current_length = len(current_chunk)
                    else:
                        current_chunk = sentence
                        current_length = sentence_length
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    current_length += sentence_length
            
            # Add final chunk
            if current_chunk.strip():
                chunk_data = {
                    "content": current_chunk.strip(),
                    "metadata": metadata or {},
                    "length": len(current_chunk.strip())
                }
                chunks.append(chunk_data)
            
            logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")
            return chunks
            
        except Exception as e:
            logger.error(f"Text chunking failed: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\\s+', ' ', text)
        
        # Normalize paragraph breaks
        text = re.sub(r'\\n\\s*\\n\\s*\\n+', '\\n\\n', text)
        
        # Strip whitespace
        text = text.strip()
        
        return text
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunk boundaries"""
        # Simple sentence splitting - could use spaCy for better results
        sentence_pattern = r'[.!?]+(?:\\s|$)'
        sentences = re.split(sentence_pattern, text)
        
        # Filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _get_overlap(self, text: str, overlap_size: int) -> str:
        """Get the last portion of text for chunk overlap"""
        if len(text) <= overlap_size:
            return text
        
        # Try to find sentence boundary in overlap region
        overlap_text = text[-overlap_size:]
        
        sentence_end = re.search(r'[.!?]+\\s+', overlap_text)
        if sentence_end:
            return overlap_text[sentence_end.end():]
        
        # Fallback to word boundary
        words = overlap_text.split()
        if len(words) > 1:
            return ' '.join(words[1:])  # Remove partial first word
        
        return overlap_text
    
    async def process_document(self, file_content: bytes, content_type: str, 
                             filename: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete document processing pipeline"""
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Extract text content
            text_content = await self.extract_text_from_file(file_content, content_type, filename)
            
            # Prepare document metadata
            doc_metadata = {
                "filename": filename,
                "content_type": content_type,
                "size": len(file_content),
                "text_length": len(text_content),
                **(metadata or {})
            }
            
            # Create chunks
            chunks = await self.chunk_text(text_content, doc_metadata)
            
            # Add document info to each chunk
            for i, chunk in enumerate(chunks):
                chunk["document_id"] = document_id
                chunk["filename"] = filename
                chunk["content_type"] = content_type
                chunk["page_number"] = i + 1
                chunk["page_start"] = i * self.chunk_size
                chunk["page_end"] = (i + 1) * self.chunk_size
                chunk["char_start"] = i * self.chunk_size
                chunk["char_end"] = (i + 1) * self.chunk_size
            
            result = {
                "document_id": document_id,
                "filename": filename,
                "content_type": content_type,
                "text_content": text_content,
                "chunks": chunks,
                "metadata": doc_metadata
            }
            
            logger.info(f"Processed document {filename}: {len(chunks)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed for {filename}: {e}")
            raise 