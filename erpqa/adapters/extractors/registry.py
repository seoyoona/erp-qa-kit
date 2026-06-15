from __future__ import annotations

from pathlib import Path
from typing import Any

from . import (
    backend_static_adapter,
    csv_adapter,
    frontend_static_adapter,
    json_yaml_adapter,
    markdown_adapter,
    procedure_sql_adapter,
    xlsx_image_manifest_adapter,
    xlsx_text_adapter,
)


REQUIRED_ADAPTERS = [
    xlsx_text_adapter,
    xlsx_image_manifest_adapter,
    csv_adapter,
    markdown_adapter,
    json_yaml_adapter,
    frontend_static_adapter,
    backend_static_adapter,
    procedure_sql_adapter,
]


def optional_adapters() -> list[Any]:
    adapters: list[Any] = []
    try:
        from . import pandas_adapter

        if pandas_adapter.available():
            adapters.append(pandas_adapter)
    except Exception:
        pass
    try:
        from . import markitdown_adapter

        if markitdown_adapter.available():
            adapters.append(markitdown_adapter)
    except Exception:
        pass
    return adapters


def registered_adapters() -> list[Any]:
    return REQUIRED_ADAPTERS + optional_adapters()


def required_adapter_names() -> list[str]:
    return [adapter.name for adapter in REQUIRED_ADAPTERS]


def select_all(path: Path, allowed_file_formats: set[str]) -> list[Any]:
    ext = path.suffix.lower()
    if ext.startswith(".") and ext[1:] not in allowed_file_formats:
        return []
    return [
        adapter
        for adapter in registered_adapters()
        if ext in adapter.supported_extensions and adapter.available()
    ]


def adapter_by_name(name: str) -> Any | None:
    for adapter in registered_adapters():
        if adapter.name == name:
            return adapter
    return None
