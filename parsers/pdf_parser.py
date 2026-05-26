import fitz
import pdfplumber
from pathlib import Path
from parsers.base_parser import BaseParser, Document

class PDFParser(BaseParser):
    def parse(self, file_path: str) -> Document:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            content = "\n\n".join(pages)
            return Document(
                content=content,
                metadata={
                    "pages": len(pdf.pages),
                },
                format="pdf",
                pages=pages
            )

    def extract_text(self, file_path: str) -> str:
        with pdfplumber.open(file_path) as pdf:
            return "\n\n".join(p.extract_text() or "" for p in pdf.pages)
