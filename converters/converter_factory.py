from pathlib import Path
from converters.base_converter import ConversionResult
from converters.libreoffice_converter import LibreOfficeConverter
from converters.native_converter import NativeConverter

class ConverterFactory:
    def __init__(self):
        try:
            self.libreoffice = LibreOfficeConverter()
        except FileNotFoundError:
            self.libreoffice = None
        self.native = NativeConverter()

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        input_ext = Path(input_path).suffix.lower()
        output_ext = Path(output_path).suffix.lower()

        lo_conversions = {
            (".doc", ".pdf"): "word",
            (".docx", ".pdf"): "word",
            (".ppt", ".pdf"): "presentation",
            (".pptx", ".pdf"): "presentation",
            (".xls", ".pdf"): "spreadsheet",
            (".xlsx", ".pdf"): "spreadsheet",
        }

        if (input_ext, output_ext) in lo_conversions:
            if self.libreoffice is None:
                return ConversionResult(success=False, error="LibreOffice not available for PDF conversion")
            return self.libreoffice.convert(input_path, output_path)

        if input_ext == ".docx" and output_ext == ".txt":
            return self.native.word_to_text(input_path, output_path)
        elif input_ext == ".pdf" and output_ext == ".txt":
            return self.native.pdf_to_text(input_path, output_path)
        elif input_ext in [".xlsx", ".xls"] and output_ext == ".csv":
            return self.native.excel_to_csv(input_path, output_path)

        return ConversionResult(success=False, error=f"Conversion {input_ext} -> {output_ext} not supported")

    def get_supported_formats(self) -> dict:
        lo_formats = [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"] if self.libreoffice is not None else []
        return {
            "libreoffice": lo_formats,
            "native": [".docx", ".pdf", ".xlsx", ".xls"]
        }
