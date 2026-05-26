from dataclasses import dataclass
from typing import List
from parsers.parser_factory import ParserFactory

@dataclass
class CheckResult:
    is_consistent: bool
    missing_fields: List[str]
    extra_fields: List[str]
    filled_fields: dict
    suggestions: List[str]

class TemplateChecker:
    def __init__(self):
        self.parser = ParserFactory()

    def check_document(self, doc_path: str, template_fields: List[str]) -> CheckResult:
        doc = self.parser.parse(doc_path)
        content = doc.content.lower()

        missing = []
        filled = {}
        for field in template_fields:
            if field.lower() in content:
                filled[field] = "Filled"
            else:
                missing.append(field)

        suggestions = []
        if missing:
            suggestions.append(f"Missing fields: {', '.join(missing)}")

        return CheckResult(
            is_consistent=len(missing) == 0,
            missing_fields=missing,
            extra_fields=[],
            filled_fields=filled,
            suggestions=suggestions
        )

    def check_multiple(self, doc_paths: List[str], template_fields: List[str]) -> List[CheckResult]:
        return [self.check_document(path, template_fields) for path in doc_paths]
