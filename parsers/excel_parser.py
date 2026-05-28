import pandas as pd
from pathlib import Path
from parsers.base_parser import BaseParser, Document

class ExcelParser(BaseParser):
    def parse(self, file_path: str) -> Document:
        path = Path(file_path)
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
            content = df.to_string()
            return Document(
                content=content,
                metadata={"format": "csv"},
                format="csv",
                pages=[content]
            )

        excel_file = pd.ExcelFile(file_path)
        sheets = {}
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            sheets[sheet_name] = df.to_string()

        all_content = "\n\n".join(
            f"[{name}]\n{content}" for name, content in sheets.items()
        )

        return Document(
            content=all_content,
            metadata={
                "sheets": excel_file.sheet_names,
                "sheet_count": len(excel_file.sheet_names)
            },
            format="xlsx",
            pages=[all_content]
        )

    def extract_text(self, file_path: str) -> str:
        return self.parse(file_path).content
