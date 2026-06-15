from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from erpqa.adapters.extractors import backend_static_adapter, frontend_static_adapter, procedure_sql_adapter
from erpqa.adapters.extractors.base import RawExtraction
from erpqa.adapters.extractors.registry import select_all
from erpqa.core.contracts import (
    EMPTY_BACKEND_CONTRACT,
    EMPTY_FRONTEND_CONTRACT,
    EMPTY_PROCEDURE_CONTRACT,
    EMPTY_SCREEN_CONTRACT,
    FRONTEND_SECTIONS,
    SECTION_NAMES,
    merge_preserving_confirmed,
    stamp_item,
)
from erpqa.core.context import RunContext
from erpqa.core.errors import ErpqaError
from erpqa.core.module_paths import module_contract_path, write_module_yaml
from erpqa.core.yaml_io import load_yaml


def _rel(ctx: RunContext, path: Any) -> str:
    """Render a file path as project-relative so generated artifacts never leak
    absolute local paths (e.g. /Users/...). Falls back to the original string
    when the path is outside the project or not resolvable."""
    raw = str(path)
    if not raw:
        return raw
    try:
        return str(Path(raw).resolve().relative_to(ctx.project_path))
    except (ValueError, OSError):
        return raw


def load_module_manifest(ctx: RunContext) -> dict[str, Any]:
    assert ctx.module is not None
    path = module_contract_path(ctx.project_path, ctx.module, "module_manifest.yaml")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ErpqaError(f"module_manifest.yaml is missing or invalid for module {ctx.module}")
    return data


def _source_paths(ctx: RunContext, kind: str) -> list[Path]:
    manifest = load_module_manifest(ctx)
    roots = manifest.get("source_roots", {}).get(kind, [])
    if isinstance(roots, str):
        roots = [roots]
    paths = [(ctx.project_path / str(root)).resolve() for root in roots]
    existing = [path for path in paths if path.exists()]
    if not existing:
        raise ErpqaError(f"no {kind} source declared for module {ctx.module}")
    return existing


def _iter_files(paths: list[Path], extensions: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        else:
            for file in sorted(path.rglob("*")):
                if file.is_file() and (extensions is None or file.suffix.lower() in extensions):
                    files.append(file)
    return sorted(files)


def generate_screen_contract(ctx: RunContext) -> Path:
    assert ctx.module is not None
    spec_roots = _source_paths(ctx, "spec")
    files = _iter_files(spec_roots)
    if not files:
        raise ErpqaError(f"no spec source files found for module {ctx.module}")
    old = load_yaml(module_contract_path(ctx.project_path, ctx.module, "screen_contract.yaml")) or {}
    contract = dict(EMPTY_SCREEN_CONTRACT)
    contract["module"] = ctx.module
    contract["screen_id"] = f"{ctx.module}_SCREEN"
    contract["screen_name"] = f"{ctx.module} Screen"
    contract["source_files"] = [str(path.relative_to(ctx.project_path)) for path in files if path.exists()]
    extraction_methods: list[str] = []
    sections = {section: [] for section in SECTION_NAMES}
    top_confidence = "medium"
    top_needs = True

    for file in files:
        adapters = select_all(file, ctx.policy.allowed_file_formats)
        if not adapters:
            continue
        for adapter in adapters:
            if adapter.name in {"pandas", "markitdown"}:
                continue
            raw = adapter.extract(file)
            extraction_methods.append(adapter.name)
            if raw.kind == "machine":
                explicit = _screen_from_explicit(ctx, raw, ctx.module)
                if explicit:
                    contract.update({key: value for key, value in explicit.items() if key != "sections"})
                    for section in SECTION_NAMES:
                        sections[section].extend(explicit.get("sections", {}).get(section, []))
                    top_confidence = "high"
                    top_needs = False
                    continue
            if raw.kind in {"tabular", "text", "structured"}:
                _apply_spec_records(ctx, raw, sections)
            elif raw.kind == "image_manifest":
                for index, record in enumerate(raw.records, start=1):
                    sections["visible_text"].append(
                        stamp_item(
                            {
                                "key": f"image_manifest_{index}",
                                "label": f"Embedded image at {record.get('sheet')}!{record.get('anchor_cell')}",
                                "visible": True,
                                "required": False,
                                "order": 9000 + index,
                            },
                            source=f"{adapter.name}:{_rel(ctx, file)}",
                            confidence="low",
                            needs_human_confirmation=True,
                        )
                    )

    old_sections = old.get("sections", {}) if isinstance(old, dict) else {}
    for section in SECTION_NAMES:
        sections[section] = merge_preserving_confirmed(old_sections.get(section, []), sections[section])
    contract["sections"] = sections
    contract["extraction_method"] = ",".join(sorted(set(extraction_methods))) or "no_available_adapter"
    contract["source"] = contract["extraction_method"]
    contract["confidence"] = top_confidence
    contract["needs_human_confirmation"] = top_needs if top_confidence == "high" else True
    return write_module_yaml(ctx.project_path, ctx.module, "screen_contract.yaml", contract)


def _screen_from_explicit(ctx: RunContext, raw: RawExtraction, module: str) -> dict[str, Any] | None:
    data = raw.records[0].get("data") if raw.records else None
    if not isinstance(data, dict) or "screen_id" not in data:
        return None
    contract = dict(EMPTY_SCREEN_CONTRACT)
    contract.update({key: data.get(key, contract.get(key)) for key in ("screen_id", "screen_name", "module")})
    contract["module"] = data.get("module") or module
    contract["source_files"] = [_rel(ctx, raw.source_path)]
    contract["extraction_method"] = raw.adapter
    contract["confidence"] = "high"
    contract["needs_human_confirmation"] = False
    sections = {section: [] for section in SECTION_NAMES}
    source_sections = data.get("sections") if isinstance(data.get("sections"), dict) else data
    for section in SECTION_NAMES:
        for item in source_sections.get(section, []) if isinstance(source_sections, dict) else []:
            if isinstance(item, dict):
                sections[section].append(
                    stamp_item(
                        item,
                        source=f"{raw.adapter}:{_rel(ctx, raw.source_path)}",
                        confidence="high",
                        needs_human_confirmation=False,
                    )
                )
    contract["sections"] = sections
    return contract


def _apply_spec_records(ctx: RunContext, raw: RawExtraction, sections: dict[str, list[dict[str, Any]]]) -> None:
    for record in raw.records:
        values = record.get("values") if isinstance(record.get("values"), dict) else None
        if values:
            lower = {str(key).lower().strip(): value for key, value in values.items()}
            section = _section_name(str(lower.get("section", "visible_text")))
            key = _slug(str(lower.get("key") or lower.get("field") or lower.get("label") or f"row_{record.get('row', len(sections[section]) + 1)}"))
            label = str(lower.get("label") or lower.get("text") or key)
            sections[section].append(
                stamp_item(
                    {
                        "key": key,
                        "label": label,
                        "visible": _bool(lower.get("visible"), True),
                        "required": _bool(lower.get("required"), False),
                        "order": _int(lower.get("order")),
                        "data_type": str(lower.get("data_type") or lower.get("type") or "string"),
                    },
                    source=f"{raw.adapter}:{_rel(ctx, raw.source_path)}",
                    confidence=raw.provenance_hint,
                    needs_human_confirmation=True,
                )
            )
        elif record.get("type") == "heading":
            key = _slug(record.get("text", "heading"))
            sections["visible_text"].append(
                stamp_item(
                    {"key": key, "label": str(record.get("text")), "visible": True, "required": False, "order": record.get("line")},
                    source=f"{raw.adapter}:{_rel(ctx, raw.source_path)}",
                    confidence="medium",
                    needs_human_confirmation=True,
                )
            )


def generate_frontend_contract(ctx: RunContext) -> Path:
    assert ctx.module is not None
    roots = _source_paths(ctx, "frontend")
    old = load_yaml(module_contract_path(ctx.project_path, ctx.module, "frontend_contract.yaml")) or {}
    contract = dict(EMPTY_FRONTEND_CONTRACT)
    contract["module"] = ctx.module
    contract["screen_id"] = f"{ctx.module}_SCREEN"
    contract["screen_name"] = f"{ctx.module} Screen"
    contract["source_files"] = [str(path.relative_to(ctx.project_path)) for path in _iter_files(roots, frontend_static_adapter.supported_extensions)]
    raw = frontend_static_adapter.extract(roots[0] if len(roots) == 1 else roots[0])
    _apply_frontend_records(ctx, raw, contract)
    for section in FRONTEND_SECTIONS:
        contract[section] = merge_preserving_confirmed(old.get(section, []), contract[section])
    return write_module_yaml(ctx.project_path, ctx.module, "frontend_contract.yaml", contract)


def _apply_frontend_records(ctx: RunContext, raw: RawExtraction, contract: dict[str, Any]) -> None:
    for record in raw.records:
        kind = record.get("kind")
        body = str(record.get("body", ""))
        source = f"{raw.adapter}:{_rel(ctx, record.get('file'))}:{record.get('line')}"
        if kind == "screen_id":
            contract["screen_id"] = body
        elif kind == "screen_name":
            contract["screen_name"] = body
        elif kind == "route":
            parts = body.split(maxsplit=1)
            contract["detected_routes_components"].append({"route": parts[0], "component": parts[1] if len(parts) > 1 else ""})
        elif kind == "api_call":
            parts = body.split(maxsplit=1)
            contract["api_calls"].append({"method": parts[0], "path": parts[1] if len(parts) > 1 else ""})
        elif kind in {"visible_text", "grid_column", "search_filter", "form_field", "button", "hidden"}:
            item = _pipe_item(body, source, "medium")
            if kind == "visible_text":
                contract["visible_text"].append(item)
            elif kind == "grid_column":
                contract["grid_columns"].append(item)
            elif kind == "search_filter":
                contract["search_filters"].append(item)
            elif kind == "form_field":
                contract["form_fields"].append(item)
            elif kind == "button":
                contract["buttons_actions"].append(item)
            else:
                contract["hidden_internal_fields"].append(item)


def generate_backend_contract(ctx: RunContext) -> Path:
    assert ctx.module is not None
    roots = _source_paths(ctx, "backend")
    files = _iter_files(roots, backend_static_adapter.supported_extensions)
    raw = backend_static_adapter.extract(roots[0])
    contract = dict(EMPTY_BACKEND_CONTRACT)
    contract["service_repository_files"] = [str(path.relative_to(ctx.project_path)) for path in files]
    for record in raw.records:
        kind = record.get("kind")
        body = str(record.get("body", ""))
        source = f"{raw.adapter}:{_rel(ctx, record.get('file'))}:{record.get('line')}"
        if kind == "endpoint":
            parts = body.split(maxsplit=2)
            contract["endpoints"].append(
                {
                    "method": parts[0],
                    "path": parts[1] if len(parts) > 1 else "",
                    "handler": parts[2] if len(parts) > 2 else "",
                    "source": source,
                    "confidence": "medium",
                    "needs_human_confirmation": True,
                }
            )
        elif kind == "dto":
            parts = body.split()
            dto = parts[0] if parts else "DTO"
            fields = []
            for field in parts[1:]:
                key, _, data_type = field.partition(":")
                fields.append(
                    {
                        "key": key,
                        "data_type": data_type or "unknown",
                        "source": source,
                        "confidence": "medium",
                        "needs_human_confirmation": True,
                    }
                )
            contract["dto_request_response_fields"].append({"dto": dto, "fields": fields})
        elif kind == "procedure":
            parts = body.split(maxsplit=1)
            contract["procedure_calls"].append({"procedure_name": parts[0], "called_from": parts[1] if len(parts) > 1 else "", "source": source, "confidence": "medium", "needs_human_confirmation": True})
        elif kind == "mapping":
            parts = body.split(maxsplit=2)
            contract["field_mapping_evidence"].append(
                {
                    "frontend_key": parts[0] if parts else "",
                    "backend_key": parts[1] if len(parts) > 1 else "",
                    "evidence": parts[2] if len(parts) > 2 else body,
                    "source": source,
                    "confidence": "medium",
                    "needs_human_confirmation": True,
                }
            )
    return write_module_yaml(ctx.project_path, ctx.module, "backend_contract.yaml", contract)


def generate_procedure_contract(ctx: RunContext) -> Path:
    assert ctx.module is not None
    roots = _source_paths(ctx, "procedure")
    raw = procedure_sql_adapter.extract(roots[0])
    contract = dict(EMPTY_PROCEDURE_CONTRACT)
    if raw.records:
        first = raw.records[0]
        contract.update(
            {
                "procedure_name": first.get("procedure_name", ""),
                "procedure_file_path": str(Path(first.get("file", raw.source_path)).relative_to(ctx.project_path)),
                "parameters": [
                    {**param, "source": f"{raw.adapter}:{_rel(ctx, first.get('file'))}", "confidence": "medium", "needs_human_confirmation": True}
                    for param in first.get("parameters", [])
                ],
                "result_columns": [
                    {**col, "source": f"{raw.adapter}:{_rel(ctx, first.get('file'))}", "confidence": "low", "needs_human_confirmation": True}
                    for col in first.get("result_columns", [])
                ],
                "tables_touched": first.get("tables_touched", []),
                "source": raw.adapter,
                "confidence": "low",
                "needs_human_confirmation": True,
                "deferred": True,
            }
        )
    return write_module_yaml(ctx.project_path, ctx.module, "procedure_contract.yaml", contract)


def _pipe_item(body: str, source: str, confidence: str) -> dict[str, Any]:
    parts = [part.strip() for part in body.split("|")]
    key = _slug(parts[0] if parts else body)
    label = parts[1] if len(parts) > 1 and parts[1] else parts[0]
    item = {
        "key": key,
        "label": label,
        "visible": True,
        "required": False,
        "source": source,
        "confidence": confidence,
        "needs_human_confirmation": True,
    }
    if len(parts) > 2 and parts[2]:
        for flag in parts[2:]:
            flag_lower = flag.lower()
            if flag_lower.isdigit():
                item["order"] = int(flag_lower)
            elif flag_lower == "required":
                item["required"] = True
            elif flag_lower == "hidden":
                item["visible"] = False
            elif flag_lower == "visible":
                item["visible"] = True
            elif flag_lower in {"readonly", "disabled", "readonly_disabled"}:
                item["readonly_disabled"] = True
    return item


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value).strip().lower()).strip("_")
    return text or "item"


def _section_name(value: str) -> str:
    aliases = {
        "columns": "grid_columns",
        "grid_column": "grid_columns",
        "filter": "search_filters",
        "filters": "search_filters",
        "field": "form_fields",
        "fields": "form_fields",
        "button": "buttons_actions",
        "buttons": "buttons_actions",
        "hidden": "hidden_fields",
    }
    normalized = value.strip().lower()
    return aliases.get(normalized, normalized if normalized in SECTION_NAMES else "visible_text")


def _bool(value: Any, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
