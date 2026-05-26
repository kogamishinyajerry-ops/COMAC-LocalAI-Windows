from ollama_client import OllamaClient
import re
import json

class AIFillAssistant:
    def __init__(self):
        self.client = OllamaClient("qwen2.5")

    def extract_fill_data(self, source_text: str, template: str, placeholders: list) -> dict:
        prompt = f"""从以下文本中提取信息，填入模板。

模板占位符: {', '.join(placeholders)}

源文档内容:
{source_text}

请以JSON格式输出提取的数据，键为占位符名称，值为提取的内容。
只输出JSON，不要其他文字。"""

        response = self.client.generate(prompt)

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}

    def suggest_template(self, source_text: str, doc_type: str) -> str:
        prompt = f"""分析以下文档，判断最适合的模板类型。

文档类型: {doc_type}
内容预览: {source_text[:1000]}

可选模板:
- 周报 (weekly_report)
- 月报 (monthly_report)
- 审批单 (approval_form)
- 邀请函 (invitation_letter)
- 通知书 (notice_letter)

只输出模板名称。"""

        response = self.client.generate(prompt)
        return response.strip()
