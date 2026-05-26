from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class Document:
    content: str
    metadata: Dict[str, Any]
    format: str
    pages: Optional[List[str]] = None

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> Document:
        pass

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        pass
