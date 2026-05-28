import subprocess
from pathlib import Path
from converters.base_converter import BaseConverter, ConversionResult

class LibreOfficeConverter(BaseConverter):
    def __init__(self, libreoffice_path=None):
        if libreoffice_path is None:
            candidates = [
                Path("tools/LibreOfficePortable/App/libreoffice/program/soffice.exe"),
                Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
                Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
            ]
            found = [str(p) for p in candidates if p.exists()]
            if not found:
                raise FileNotFoundError(
                    "LibreOffice not found. Expected paths:\n  " +
                    "\n  ".join(str(p) for p in candidates)
                )
            self.libreoffice = found[0]
        else:
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
