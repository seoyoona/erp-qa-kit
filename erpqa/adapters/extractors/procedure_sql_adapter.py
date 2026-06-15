from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import RawExtraction


name = "procedure_sql"
supported_extensions = frozenset({".sql"})
tier = "REQUIRED"


def available() -> bool:
    return True


def extract(path: Path) -> RawExtraction:
    files = [path] if path.is_file() else sorted(file for file in path.rglob("*.sql") if file.is_file())
    records: list[dict[str, Any]] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        proc_match = re.search(r"\b(?:CREATE|ALTER)\s+(?:PROCEDURE|PROC)\s+([\w\.\[\]]+)", text, re.IGNORECASE)
        proc_name = proc_match.group(1).strip("[]") if proc_match else file.stem
        params = [
            {"name": match.group(1), "data_type": match.group(2)}
            for match in re.finditer(r"(@\w+)\s+([A-Za-z0-9_\(\)]+)", text)
        ]
        select_match = re.search(r"\bSELECT\s+(.*?)\s+FROM\s", text, re.IGNORECASE | re.DOTALL)
        columns: list[dict[str, str]] = []
        if select_match:
            for raw_col in select_match.group(1).split(","):
                col = raw_col.strip().split()[-1].strip("[]")
                if col and col != "*":
                    columns.append({"key": col, "data_type": "unknown"})
        tables = sorted(
            {
                match.group(2).strip("[]")
                for match in re.finditer(r"\b(FROM|JOIN|UPDATE|INTO)\s+([\w\.\[\]]+)", text, re.IGNORECASE)
            }
        )
        records.append(
            {
                "procedure_name": proc_name,
                "file": file.as_posix(),
                "parameters": params,
                "result_columns": columns,
                "tables_touched": tables,
                "dynamic_sql": bool(re.search(r"\bEXEC\s*\(", text, re.IGNORECASE)),
            }
        )
    return RawExtraction(path.as_posix(), "procedure", records, "low", [], name)

