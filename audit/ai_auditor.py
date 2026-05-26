from ollama_client import OllamaClient
from parsers.parser_factory import ParserFactory
from dataclasses import dataclass
from typing import List
import json
import re

@dataclass
class AuditFinding:
    category: str
    description: str
    suggestion: str
    severity: str

@dataclass
class AuditResult:
    is_approved: bool
    findings: List[AuditFinding]
    overall_comment: str

class AIAuditor:
    def __init__(self):
        self.qwen = OllamaClient("qwen2.5")
        self.parser = ParserFactory()

    def audit_document(self, file_path: str, criteria: str = None) -> AuditResult:
        doc = self.parser.parse(file_path)
        content = doc.content[:8000]

        prompt = f"""Please audit the following document:
1. Content completeness
2. Format compliance
3. Logical consistency
4. Potential issues

Criteria: {criteria or "Standard business document guidelines"}

Document content:
{content}

Please output JSON with:
- is_approved: boolean
- findings: list of issues
- overall_comment: summary"""

        response = self.qwen.generate(prompt)

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                result_data = json.loads(json_match.group())
                return AuditResult(
                    is_approved=result_data.get("is_approved", False),
                    findings=[
                        AuditFinding(
                            category=f.get("category", "general"),
                            description=f.get("description", ""),
                            suggestion=f.get("suggestion", ""),
                            severity=f.get("severity", "medium")
                        ) for f in result_data.get("findings", [])
                    ],
                    overall_comment=result_data.get("overall_comment", "")
                )
            except:
                pass

        return AuditResult(is_approved=False, findings=[], overall_comment="Audit failed to parse response")

    def quick_check(self, text: str) -> str:
        prompt = f"""Quick check: Is there any obvious problem with this content?
(Political sensitivity, violence, illegal content, etc.)
If there are issues, describe them. If not, reply "Check passed".

Content: {text[:2000]}"""

        return self.qwen.generate(prompt)
