from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .base import RawExtraction


name = "json_yaml"
supported_extensions = frozenset({".json", ".yaml", ".yml"})
tier = "REQUIRED"


def available() -> bool:
    return True


def extract(path: Path) -> RawExtraction:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text) if text.strip() else {}
    explicit = isinstance(data, dict) and "screen_id" in data and (
        "sections" in data or any(key in data for key in ("grid_columns", "form_fields", "search_filters"))
    )
    return RawExtraction(
        source_path=path.as_posix(),
        kind="machine" if explicit else "structured",
        records=[{"data": data, "explicit_contract": explicit}],
        provenance_hint="high" if explicit else "medium",
        notes=[],
        adapter=name,
    )

