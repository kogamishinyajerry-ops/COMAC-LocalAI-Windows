from pathlib import Path
from dataclasses import dataclass
from typing import List
import difflib

@dataclass
class DiffResult:
    added_lines: List[str]
    removed_lines: List[str]
    changed_lines: List[str]
    similarity: float
    diff_html: str

class DocumentDiff:
    def compare(self, old_text: str, new_text: str) -> DiffResult:
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        similarity = matcher.ratio()

        diff = list(matcher.get_opcodes())

        added = []
        removed = []
        changed = []

        for tag, i1, i2, j1, j2 in diff:
            if tag == 'equal':
                continue
            elif tag == 'insert':
                added.extend(new_lines[j1:j2])
            elif tag == 'delete':
                removed.extend(old_lines[i1:i2])
            elif tag == 'replace':
                changed.append(f"行 {i1+1}: {old_lines[i1]} -> {new_lines[j1]}")

        diff_generator = difflib.HtmlDiff()
        html = diff_generator.make_table(
            old_lines, new_lines,
            fromdesc='Old Version',
            todesc='New Version'
        )

        return DiffResult(
            added_lines=added,
            removed_lines=removed,
            changed_lines=changed,
            similarity=similarity,
            diff_html=html
        )

    def compare_files(self, old_path: str, new_path: str) -> DiffResult:
        with open(old_path, "r", encoding="utf-8") as f:
            old_text = f.read()
        with open(new_path, "r", encoding="utf-8") as f:
            new_text = f.read()
        return self.compare(old_text, new_text)
