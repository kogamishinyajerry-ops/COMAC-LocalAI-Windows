from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ConversionResult:
    success: bool
    output_path: Optional[str] = None
    error: Optional[str] = None

class BaseConverter(ABC):
    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        pass
