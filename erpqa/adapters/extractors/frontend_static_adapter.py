from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import RawExtraction


name = "frontend_static"
supported_extensions = frozenset({".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".html"})
tier = "REQUIRED"
ANNOTATION = re.compile(r"erpqa:(?P<kind>[a-z_]+)\s+(?P<body>.+)")


def available() -> bool:
    return True


def extract(path: Path) -> RawExtraction:
    files = [path] if path.is_file() else sorted(
        file for file in path.rglob("*") if file.is_file() and file.suffix.lower() in supported_extensions
    )
    records: list[dict[str, Any]] = []
    for file in files:
        rel = file.as_posix()
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, start=1):
            match = ANNOTATION.search(line)
            if match:
                records.append(
                    {
                        "kind": match.group("kind"),
                        "body": match.group("body").strip(),
                        "file": rel,
                        "line": line_no,
                        "direct_literal": True,
                    }
                )
            for literal in re.findall(r">([^<>{}\n]{2,80})<", line):
                records.append(
                    {
                        "kind": "visible_text",
                        "body": literal.strip(),
                        "file": rel,
                        "line": line_no,
                        "direct_literal": True,
                    }
                )
    return RawExtraction(path.as_posix(), "frontend", records, "medium", [], name)

