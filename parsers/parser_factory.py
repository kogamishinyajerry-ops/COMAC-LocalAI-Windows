from pathlib import Path
from parsers.base_parser import BaseParser, Document
from parsers.docx_parser import WordParser
from parsers.pdf_parser import PDFParser
from parsers.pptx_parser import PPTParser
from parsers.excel_parser import ExcelParser
from parsers.txt_parser import TextParser

class ParserFactory:
    _parsers = {
        ".docx": WordParser(),
        ".pdf": PDFParser(),
        ".pptx": PPTParser(),
        ".xlsx": ExcelParser(),
        ".csv": ExcelParser(),
        ".txt": TextParser(),
        ".md": TextParser(),
    }

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        ext = Path(file_path).suffix.lower()
        if ext not in cls._parsers:
            raise ValueError(f"Unsupported format: {ext}")
        return cls._parsers[ext]

    @classmethod
    def parse(cls, file_path: str) -> Document:
        return cls.get_parser(file_path).parse(file_path)

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        return cls.get_parser(file_path).extract_text(file_path)
