from pathlib import Path
from converters.base_converter import BaseConverter, ConversionResult

class NativeConverter(BaseConverter):
    def word_to_text(self, input_path: str, output_path: str) -> ConversionResult:
        from docx import Document
        try:
            doc = Document(input_path)
            texts = [p.text for p in doc.paragraphs if p.text.strip()]
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(texts))
            return ConversionResult(success=True, output_path=output_path)
        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def pdf_to_text(self, input_path: str, output_path: str) -> ConversionResult:
        import fitz
        try:
            doc = fitz.open(input_path)
            texts = [page.get_text() for page in doc]
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(texts))
            return ConversionResult(success=True, output_path=output_path)
        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def excel_to_csv(self, input_path: str, output_path: str) -> ConversionResult:
        import pandas as pd
        try:
            df = pd.read_excel(input_path)
            df.to_csv(output_path, index=False, encoding="utf-8")
            return ConversionResult(success=True, output_path=output_path)
        except Exception as e:
            return ConversionResult(success=False, error=str(e))

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        input_ext = Path(input_path).suffix.lower()
        output_ext = Path(output_path).suffix.lower()

        if input_ext == ".docx" and output_ext == ".txt":
            return self.word_to_text(input_path, output_path)
        elif input_ext == ".pdf" and output_ext == ".txt":
            return self.pdf_to_text(input_path, output_path)
        elif input_ext in [".xlsx", ".xls"] and output_ext == ".csv":
            return self.excel_to_csv(input_path, output_path)

        return ConversionResult(success=False, error=f"Native conversion {input_ext} -> {output_ext} not supported")
