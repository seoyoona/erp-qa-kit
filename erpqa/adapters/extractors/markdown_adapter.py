from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import RawExtraction


name = "markdown"
supported_extensions = frozenset({".md"})
tier = "REQUIRED"


def available() -> bool:
    return True


def extract(path: Path) -> RawExtraction:
    records: list[dict[str, Any]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            records.append({"type": "heading", "level": level, "text": stripped[level:].strip(), "line": index + 1})
        elif stripped.startswith(("- ", "* ")):
            records.append({"type": "list_item", "text": stripped[2:].strip(), "line": index + 1})
        elif stripped.startswith("|") and stripped.endswith("|"):
            header = [cell.strip() for cell in stripped.strip("|").split("|")]
            if index + 1 < len(lines) and set(lines[index + 1].replace("|", "").strip()) <= {"-", ":", " "}:
                row_index = index + 2
                while row_index < len(lines) and lines[row_index].strip().startswith("|"):
                    row = [cell.strip() for cell in lines[row_index].strip().strip("|").split("|")]
                    records.append(
                        {
                            "type": "table_row",
                            "line": row_index + 1,
                            "values": {header[col]: row[col] if col < len(row) else "" for col in range(len(header))},
                        }
                    )
                    row_index += 1
                index = row_index - 1
        elif stripped:
            records.append({"type": "paragraph", "text": stripped, "line": index + 1})
        index += 1
    return RawExtraction(path.as_posix(), "text", records, "medium", [], name)

