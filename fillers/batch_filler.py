from pathlib import Path
from fillers.template_engine import TemplateEngine
from dataclasses import dataclass
from typing import Optional

@dataclass
class FillResult:
    success: bool
    template_name: str
    output_path: Optional[str] = None
    error: Optional[str] = None

class BatchFiller:
    def __init__(self, template_dir: str = "templates", output_dir: str = "temp/outputs"):
        self.engine = TemplateEngine(template_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fill_single(self, template_name: str, data: dict, output_name: str = None) -> FillResult:
        try:
            output_name = output_name or f"{template_name}_filled.txt"
            output_path = self.output_dir / output_name

            content = self.engine.render(template_name, data)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            return FillResult(success=True, template_name=template_name, output_path=str(output_path))

        except Exception as e:
            return FillResult(success=False, template_name=template_name, error=str(e))

    def fill_from_csv(self, template_name: str, csv_path: str) -> list:
        import pandas as pd

        df = pd.read_csv(csv_path)
        results = []

        for idx, row in df.iterrows():
            data = row.to_dict()
            output_name = f"{template_name}_{idx+1}.txt"
            result = self.fill_single(template_name, data, output_name)
            results.append(result)

        return results
