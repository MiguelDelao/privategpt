"""
Document processing utilities for PrivateGPT UI (v2).
Handles text extraction from various document formats. Mirrors v1 behaviour for
compatibility.  Requires PyPDF2 and python-docx which are added to the
requirements for the ui service.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import PyPDF2
from docx import Document


class DocumentProcessor:  # noqa: D101
    def __init__(self):
        self.supported_formats = [".pdf", ".docx", ".txt"]

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def extract_text(self, uploaded_file):  # noqa: ANN001, D401
        """Extract text from uploaded file (BytesIO)."""
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension == ".pdf":
            return self._extract_pdf_text(uploaded_file)
        if file_extension == ".docx":
            return self._extract_docx_text(uploaded_file)
        if file_extension == ".txt":
            return self._extract_txt_text(uploaded_file)
        raise ValueError(f"Unsupported file format: {file_extension}")

    def validate_file(self, uploaded_file):  # noqa: ANN001, D401
        max_size = 50 * 1024 * 1024  # 50 MB
        if uploaded_file.size > max_size:
            return False, "File too large (50 MB max)"
        ext = Path(uploaded_file.name).suffix.lower()
        if ext not in self.supported_formats:
            return False, f"Unsupported file type: {ext}"
        return True, None

    def get_file_info(self, uploaded_file):  # noqa: ANN001, D401
        return {
            "filename": uploaded_file.name,
            "size": uploaded_file.size,
            "type": uploaded_file.type,
            "extension": Path(uploaded_file.name).suffix.lower(),
            "document_type": self.get_document_type(uploaded_file.name),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_pdf_text(self, uploaded_file):  # noqa: ANN001
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            text_content: list[str] = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as exc:  # noqa: BLE001
                    text_content.append(
                        f"--- Page {page_num + 1} ---\n[Error extracting text: {exc}]")
            return "\n\n".join(text_content)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Error processing PDF: {exc}")

    def _extract_docx_text(self, uploaded_file):  # noqa: ANN001
        try:
            doc = Document(io.BytesIO(uploaded_file.read()))
            text_content = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(text_content)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Error processing DOCX: {exc}")

    def _extract_txt_text(self, uploaded_file):  # noqa: ANN001
        try:
            try:
                content = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode("latin-1")
            return content
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Error processing TXT: {exc}")

    def get_document_type(self, filename: str) -> str:  # noqa: D401
        fname = filename.lower()
        if any(word in fname for word in ["contract", "agreement", "lease", "nda"]):
            return "contract"
        if any(word in fname for word in ["case", "court", "ruling", "decision"]):
            return "case_law"
        if any(word in fname for word in ["filing", "motion", "brief", "pleading"]):
            return "filing"
        if any(word in fname for word in ["memo", "memorandum", "opinion"]):
            return "memo"
        if any(word in fname for word in ["statute", "regulation", "code"]):
            return "statute"
        return "document" 