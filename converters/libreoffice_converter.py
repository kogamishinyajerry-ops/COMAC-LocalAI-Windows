import subprocess
from pathlib import Path
from converters.base_converter import BaseConverter, ConversionResult

class LibreOfficeConverter(BaseConverter):
    def __init__(self, libreoffice_path="/usr/bin/soffice"):
        self.libreoffice = libreoffice_path

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            output_dir = Path(output_path).parent.absolute()

            cmd = [
                self.libreoffice,
                "--headless",
                "--convert-to", Path(output_path).suffix[1:],
                "--outdir", str(output_dir),
                str(input_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and Path(output_path).exists():
                return ConversionResult(success=True, output_path=output_path)
            else:
                return ConversionResult(success=False, error=result.stderr)

        except subprocess.TimeoutExpired:
            return ConversionResult(success=False, error="Conversion timeout")
        except FileNotFoundError:
            return ConversionResult(success=False, error="LibreOffice not found. Please install LibreOffice.")
        except Exception as e:
            return ConversionResult(success=False, error=str(e))
