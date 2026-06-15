from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .base import RawExtraction


name = "csv"
supported_extensions = frozenset({".csv"})
tier = "REQUIRED"


def available() -> bool:
    return True


def extract(path: Path) -> RawExtraction:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return RawExtraction(path.as_posix(), "tabular", [], "medium", ["empty CSV"], name)
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(text.splitlines(), dialect)
    rows = list(reader)
    if not rows:
        return RawExtraction(path.as_posix(), "tabular", [], "medium", ["no rows"], name)
    header = [cell.strip() for cell in rows[0]]
    records: list[dict[str, Any]] = []
    notes: list[str] = []
    for row_index, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            notes.append(f"ragged row {row_index}: expected {len(header)} cells, got {len(row)}")
        values = {header[index]: row[index].strip() if index < len(row) else "" for index in range(len(header))}
        records.append({"row": row_index, "values": values})
    return RawExtraction(path.as_posix(), "tabular", records, "medium", notes, name)

