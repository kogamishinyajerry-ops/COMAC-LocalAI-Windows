from pathlib import Path
from batch.batch_processor import BatchProcessor, BatchResult
from parsers.parser_factory import ParserFactory
from ollama_client import OllamaClient

class BatchSummarizer:
    def __init__(self, max_workers: int = 4):
        self.processor = BatchProcessor(max_workers)
        self.parser = ParserFactory()
        self.client = OllamaClient("qwen2.5")

    def add_file(self, input_path: str, output_path: str = None):
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".summary.txt"))
        self.processor.add_task(input_path, output_path)

    def execute(self) -> BatchResult:
        def summarize_func(input_path: str, output_path: str) -> dict:
            doc = self.parser.parse(input_path)
            content = doc.content[:5000]

            prompt = f"请总结以下文档的要点，字数控制在200字以内：\n\n{content}"
            summary = self.client.generate(prompt)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"原始文件: {input_path}\n\n")
                f.write(f"文档摘要:\n{summary}")

            return {"success": True, "summary": summary}

        return self.processor.process(summarize_func)
