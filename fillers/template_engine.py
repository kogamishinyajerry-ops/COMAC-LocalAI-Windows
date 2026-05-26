from jinja2 import Template, Environment, BaseLoader
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any
import re

@dataclass
class TemplateDefinition:
    name: str
    description: str
    template_path: str
    placeholders: list
    sample_data: Dict[str, str]

class TemplateEngine:
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.env = Environment(loader=BaseLoader())

    def load_template(self, template_name: str) -> TemplateDefinition:
        template_file = self.template_dir / f"{template_name}.jinja2"
        data_file = self.template_dir / f"{template_name}.json"

        if not template_file.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()

        placeholders = list(set(re.findall(r'\{\{(\w+)\}\}', content)))

        sample_data = {}
        if data_file.exists():
            import json
            with open(data_file, "r", encoding="utf-8") as f:
                sample_data = json.load(f)

        return TemplateDefinition(
            name=template_name,
            description="",
            template_path=str(template_file),
            placeholders=list(set(placeholders)),
            sample_data=sample_data
        )

    def render(self, template_name: str, data: Dict[str, Any]) -> str:
        template_file = self.template_dir / f"{template_name}.jinja2"
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()

        template = self.env.from_string(template_content)
        return template.render(**data)

    def validate_data(self, template_name: str, data: Dict[str, Any]) -> tuple:
        tmpl = self.load_template(template_name)
        missing = [p for p in tmpl.placeholders if p not in data]
        extra = [k for k in data.keys() if k not in tmpl.placeholders]
        return missing, extra
