from __future__ import annotations

from typing import Iterable


def result(missing: list[str] | None = None, errors: list[str] | None = None) -> dict:
    missing = missing or []
    errors = errors or []
    return {"pass": not missing and not errors, "missing": missing, "errors": errors}


def require_fields(data: dict, fields: Iterable[str], prefix: str) -> list[str]:
    missing: list[str] = []
    for field in fields:
        if data.get(field) in (None, "", []):
            missing.append(f"{prefix}.{field}")
    return missing


def list_items(data: dict, key: str) -> list[dict]:
    items = data.get(key, [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]
