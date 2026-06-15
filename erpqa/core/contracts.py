from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import CONFIDENCE_VALUES
from .validation import ValidationIssue
from .yaml_io import load_yaml


SECTION_NAMES = [
    "visible_text",
    "search_filters",
    "grid_columns",
    "form_fields",
    "buttons_actions",
    "hidden_fields",
]
FRONTEND_SECTIONS = [
    "visible_text",
    "search_filters",
    "grid_columns",
    "form_fields",
    "buttons_actions",
    "hidden_internal_fields",
]


EMPTY_SCREEN_CONTRACT: dict[str, Any] = {
    "screen_id": "",
    "screen_name": "",
    "module": "",
    "source_files": [],
    "extraction_method": "module-init scaffold",
    "source": "module-init scaffold",
    "confidence": "medium",
    "needs_human_confirmation": True,
    "sections": {
        "visible_text": [],
        "search_filters": [],
        "grid_columns": [],
        "form_fields": [],
        "buttons_actions": [],
        "hidden_fields": [],
    },
}

EMPTY_FRONTEND_CONTRACT: dict[str, Any] = {
    "screen_id": "",
    "screen_name": "",
    "module": "",
    "source_files": [],
    "extraction_method": "module-init scaffold",
    "detected_routes_components": [],
    "api_calls": [],
    "visible_text": [],
    "search_filters": [],
    "grid_columns": [],
    "form_fields": [],
    "buttons_actions": [],
    "hidden_internal_fields": [],
    "source": "module-init scaffold",
    "confidence": "medium",
    "needs_human_confirmation": True,
}

EMPTY_BACKEND_CONTRACT: dict[str, Any] = {
    "endpoints": [],
    "dto_request_response_fields": [],
    "service_repository_files": [],
    "procedure_calls": [],
    "field_mapping_evidence": [],
    "source": "module-init scaffold",
    "confidence": "medium",
    "needs_human_confirmation": True,
}

EMPTY_PROCEDURE_CONTRACT: dict[str, Any] = {
    "procedure_name": "",
    "procedure_file_path": "",
    "parameters": [],
    "result_columns": [],
    "tables_touched": [],
    "source": "module-init scaffold",
    "confidence": "low",
    "needs_human_confirmation": True,
    "deferred": True,
}


def empty_contracts(module: str) -> dict[str, dict[str, Any]]:
    screen = deepcopy(EMPTY_SCREEN_CONTRACT)
    screen["module"] = module
    frontend = deepcopy(EMPTY_FRONTEND_CONTRACT)
    frontend["module"] = module
    return {
        "screen_contract.yaml": screen,
        "frontend_contract.yaml": frontend,
        "backend_contract.yaml": deepcopy(EMPTY_BACKEND_CONTRACT),
        "procedure_contract.yaml": deepcopy(EMPTY_PROCEDURE_CONTRACT),
    }


def contract_items(contract: dict[str, Any], contract_type: str) -> list[dict[str, Any]]:
    if contract_type == "screen":
        sections = contract.get("sections") or {}
        return [
            item
            for section in SECTION_NAMES
            for item in (sections.get(section) or [])
            if isinstance(item, dict)
        ]
    if contract_type == "frontend":
        return [
            item
            for section in FRONTEND_SECTIONS
            for item in (contract.get(section) or [])
            if isinstance(item, dict)
        ]
    if contract_type == "backend":
        items: list[dict[str, Any]] = []
        for endpoint in contract.get("endpoints") or []:
            if isinstance(endpoint, dict):
                items.append(endpoint)
        for field_group in contract.get("dto_request_response_fields") or []:
            if isinstance(field_group, dict):
                for field in field_group.get("fields") or []:
                    if isinstance(field, dict):
                        items.append(field)
        for mapping in contract.get("field_mapping_evidence") or []:
            if isinstance(mapping, dict):
                items.append(mapping)
        return items
    if contract_type == "procedure":
        return [
            item
            for key in ("parameters", "result_columns")
            for item in (contract.get(key) or [])
            if isinstance(item, dict)
        ]
    return []


def stamp_item(
    item: dict[str, Any],
    *,
    source: str,
    confidence: str,
    needs_human_confirmation: bool,
) -> dict[str, Any]:
    stamped = dict(item)
    stamped.setdefault("source", source)
    stamped.setdefault("confidence", confidence)
    stamped.setdefault("needs_human_confirmation", needs_human_confirmation)
    if stamped["confidence"] in {"low", "medium"}:
        stamped["needs_human_confirmation"] = True
    return stamped


def merge_preserving_confirmed(
    old_items: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    confirmed = {
        item.get("key"): item
        for item in old_items
        if isinstance(item, dict)
        and item.get("key")
        and item.get("needs_human_confirmation") is False
    }
    merged: list[dict[str, Any]] = []
    for item in new_items:
        key = item.get("key")
        merged.append(dict(confirmed.get(key, item)))
    existing_keys = {item.get("key") for item in merged}
    for key, item in sorted(confirmed.items()):
        if key not in existing_keys:
            merged.append(dict(item))
    return merged


def validate_contract_file(path: Path, contract_type: str | None = None) -> list[ValidationIssue]:
    data = load_yaml(path)
    if data is None:
        return []
    if not isinstance(data, dict):
        return [ValidationIssue(str(path), path.name, "type", "expected a YAML mapping")]
    ctype = contract_type or _type_from_name(path.name)
    issues: list[ValidationIssue] = []
    if ctype == "screen":
        issues.extend(_required(path, data, ["screen_id", "screen_name", "module", "source_files", "extraction_method", "confidence", "needs_human_confirmation", "sections"]))
        sections = data.get("sections")
        if not isinstance(sections, dict):
            issues.append(ValidationIssue(str(path), "sections", "type", "sections mapping is required"))
        else:
            for section in SECTION_NAMES:
                if section not in sections or not isinstance(sections.get(section), list):
                    issues.append(ValidationIssue(str(path), f"sections.{section}", "missing", "section list is required"))
                for index, item in enumerate(sections.get(section) or []):
                    issues.extend(_validate_contract_item(path, item, f"sections.{section}[{index}]"))
    elif ctype == "frontend":
        issues.extend(_required(path, data, ["screen_id", "module", "source_files", "extraction_method", "detected_routes_components", *FRONTEND_SECTIONS, "source", "confidence", "needs_human_confirmation"]))
        for section in FRONTEND_SECTIONS:
            if section in data and not isinstance(data.get(section), list):
                issues.append(ValidationIssue(str(path), section, "type", "expected a list"))
            for index, item in enumerate(data.get(section) or []):
                issues.extend(_validate_contract_item(path, item, f"{section}[{index}]"))
    elif ctype == "backend":
        issues.extend(_required(path, data, ["endpoints", "dto_request_response_fields", "service_repository_files", "field_mapping_evidence", "source", "confidence", "needs_human_confirmation"]))
        for index, item in enumerate(contract_items(data, "backend")):
            issues.extend(_validate_provenance(path, item, f"backend_items[{index}]"))
    elif ctype == "procedure":
        issues.extend(_required(path, data, ["procedure_name", "procedure_file_path", "parameters", "source", "confidence", "needs_human_confirmation"]))
        for index, item in enumerate(contract_items(data, "procedure")):
            issues.extend(_validate_provenance(path, item, f"procedure_items[{index}]"))
    issues.extend(_validate_provenance(path, data, ctype or path.name))
    return issues


def _type_from_name(name: str) -> str:
    if name.startswith("screen_"):
        return "screen"
    if name.startswith("frontend_"):
        return "frontend"
    if name.startswith("backend_"):
        return "backend"
    if name.startswith("procedure_"):
        return "procedure"
    return ""


def _required(path: Path, data: dict[str, Any], fields: list[str]) -> list[ValidationIssue]:
    return [
        ValidationIssue(str(path), field, "missing", "required field is missing")
        for field in fields
        if field not in data
    ]


def _validate_contract_item(path: Path, item: Any, locator: str) -> list[ValidationIssue]:
    if not isinstance(item, dict):
        return [ValidationIssue(str(path), locator, "type", "expected a mapping")]
    issues: list[ValidationIssue] = []
    for field in ("key", "label", "visible", "required"):
        if field not in item:
            issues.append(ValidationIssue(str(path), f"{locator}.{field}", "missing", "required field is missing"))
    issues.extend(_validate_provenance(path, item, locator))
    return issues


def _validate_provenance(path: Path, item: dict[str, Any], locator: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in ("source", "confidence", "needs_human_confirmation"):
        if field not in item:
            issues.append(ValidationIssue(str(path), f"{locator}.{field}", "missing", "required provenance field is missing"))
    confidence = item.get("confidence")
    if confidence is not None and confidence not in CONFIDENCE_VALUES:
        issues.append(ValidationIssue(str(path), f"{locator}.confidence", "enum", "confidence must be high, medium, or low"))
    needs = item.get("needs_human_confirmation")
    if needs is not None and not isinstance(needs, bool):
        issues.append(ValidationIssue(str(path), f"{locator}.needs_human_confirmation", "type", "needs_human_confirmation must be boolean"))
    if confidence in {"low", "medium"} and needs is False:
        issues.append(
            ValidationIssue(
                str(path),
                f"{locator}.needs_human_confirmation",
                "human_confirmation",
                "low/medium confidence items must require human confirmation",
            )
        )
    return issues
