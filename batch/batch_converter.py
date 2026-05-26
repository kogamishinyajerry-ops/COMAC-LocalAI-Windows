from pathlib import Path
from batch.batch_processor import BatchProcessor, BatchResult
from converters.converter_factory import ConverterFactory

class BatchConverter:
    def __init__(self, max_workers: int = 4):
        self.processor = BatchProcessor(max_workers)
        self.factory = ConverterFactory()

    def add_file(self, input_path: str, output_path: str):
        self.processor.add_task(input_path, output_path)

    def add_directory(self, input_dir: str, output_dir: str, pattern: str = "*.*"):
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for file in input_path.glob(pattern):
            out_file = output_path / f"{file.stem}_converted{file.suffix}"
            self.processor.add_task(str(file), str(out_file))

    def execute(self) -> BatchResult:
        def convert_func(input_path: str, output_path: str) -> dict:
            result = self.factory.convert(input_path, output_path)
            return {
                "success": result.success,
                "output_path": result.output_path,
                "error": result.error
            }

        return self.processor.process(convert_func)
