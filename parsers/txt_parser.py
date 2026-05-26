from pathlib import Path
from parsers.base_parser import BaseParser, Document

class TextParser(BaseParser):
    """TXT文件解析器"""

    def parse(self, file_path: str) -> Document:
        text = self.extract_text(file_path)
        return Document(
            content=text,
            metadata={"title": Path(file_path).stem, "word_count": len(text)},
            format="txt",
            pages=[text]
        )

    def extract_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
