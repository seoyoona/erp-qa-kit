from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import SEVERITY_VALUES
from .context import RunContext
from .module_paths import module_contract_path, write_module_yaml
from .yaml_io import load_yaml


CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class CompareResult:
    findings: list[dict[str, Any]]
    deferred: list[str]


def compare_contracts(ctx: RunContext) -> CompareResult:
    assert ctx.module is not None
    screen = load_yaml(module_contract_path(ctx.project_path, ctx.module, "screen_contract.yaml")) or {}
    frontend = load_yaml(module_contract_path(ctx.project_path, ctx.module, "frontend_contract.yaml")) or {}
    backend = load_yaml(module_contract_path(ctx.project_path, ctx.module, "backend_contract.yaml")) or {}
    findings: list[dict[str, Any]] = []

    _compare_section(ctx, findings, screen, frontend, backend, "grid_columns", "grid_columns")
    _compare_section(ctx, findings, screen, frontend, backend, "search_filters", "search_filters")
    _compare_section(ctx, findings, screen, frontend, backend, "form_fields", "form_fields")
    _compare_section(ctx, findings, screen, frontend, backend, "buttons_actions", "buttons_actions")
    _compare_section(ctx, findings, screen, frontend, backend, "visible_text", "visible_text")
    _detect_hidden_exposure(ctx, findings, screen, frontend, backend)
    findings = sorted(findings, key=lambda item: (item["screen_id"], item["mismatch_type"], item.get("field_key", "")))
    write_module_yaml(
        ctx.project_path,
        ctx.module,
        "comparison_findings.yaml",
        {
            "module": ctx.module,
            "project_memory_read": ctx.memory.read_record.project_memory_read,
            "module_memory_read": ctx.memory.read_record.module_memory_read,
            "deferred": list(ctx.policy.deferred_steps),
            "findings": findings,
        },
    )
    return CompareResult(findings=findings, deferred=list(ctx.policy.deferred_steps))


def _compare_section(
    ctx: RunContext,
    findings: list[dict[str, Any]],
    screen: dict[str, Any],
    frontend: dict[str, Any],
    backend: dict[str, Any],
    section: str,
    frontend_section: str,
) -> None:
    truth_items = _by_key((screen.get("sections") or {}).get(section) or [])
    frontend_items = _by_key(frontend.get(frontend_section) or [])
    for key, truth in truth_items.items():
        actual = frontend_items.get(key)
        if actual is None:
            findings.append(_finding(ctx, screen, frontend, backend, section, "MissingInFrontend", truth, None, "add-field-or-column"))
            if section == "grid_columns":
                findings.append(_finding(ctx, screen, frontend, backend, section, "GridColumnMismatch", truth, None, "add-column"))
            elif section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", truth, None, "add-field"))
            elif section == "search_filters":
                findings.append(_finding(ctx, screen, frontend, backend, section, "SearchFilterMismatch", truth, None, "add-filter"))
            elif section == "buttons_actions":
                findings.append(_finding(ctx, screen, frontend, backend, section, "ButtonsActionsMismatch", truth, None, "add-button"))
            continue
        if truth.get("label") != actual.get("label"):
            findings.append(_finding(ctx, screen, frontend, backend, section, "LabelMismatch", truth, actual, "rename-label"))
            if section == "search_filters":
                findings.append(_finding(ctx, screen, frontend, backend, section, "SearchFilterMismatch", truth, actual, "rename-filter-label"))
            elif section == "grid_columns":
                findings.append(_finding(ctx, screen, frontend, backend, section, "GridColumnMismatch", truth, actual, "rename-column-label"))
            elif section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", truth, actual, "rename-field-label"))
            elif section == "buttons_actions":
                findings.append(_finding(ctx, screen, frontend, backend, section, "ButtonsActionsMismatch", truth, actual, "rename-button-label"))
            if not ctx.policy.frontend_override_allowed(_aspect(section)):
                findings.append(_finding(ctx, screen, frontend, backend, section, "FrontendOverrideForbidden", truth, actual, "conform-frontend-to-source-of-truth"))
        if truth.get("order") is not None and actual.get("order") is not None and truth.get("order") != actual.get("order"):
            findings.append(_finding(ctx, screen, frontend, backend, section, "OrderMismatch", truth, actual, "reorder"))
            if section == "grid_columns":
                findings.append(_finding(ctx, screen, frontend, backend, section, "GridColumnMismatch", truth, actual, "reorder-column"))
        if "visible" in truth and "visible" in actual and truth.get("visible") != actual.get("visible"):
            findings.append(_finding(ctx, screen, frontend, backend, section, "VisibilityMismatch", truth, actual, "change-visibility"))
            if section == "search_filters":
                findings.append(_finding(ctx, screen, frontend, backend, section, "SearchFilterMismatch", truth, actual, "change-filter-visibility"))
            elif section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", truth, actual, "change-field-visibility"))
            elif section == "buttons_actions":
                findings.append(_finding(ctx, screen, frontend, backend, section, "ButtonsActionsMismatch", truth, actual, "change-button-visibility"))
        if "required" in truth and "required" in actual and truth.get("required") != actual.get("required"):
            findings.append(_finding(ctx, screen, frontend, backend, section, "RequiredFlagMismatch", truth, actual, "change-required"))
            if section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", truth, actual, "change-required"))
        if truth.get("readonly_disabled") is not None and actual.get("readonly_disabled") is not None and truth.get("readonly_disabled") != actual.get("readonly_disabled"):
            findings.append(_finding(ctx, screen, frontend, backend, section, "ReadonlyDisabledMismatch", truth, actual, "change-readonly-disabled"))
            if section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", truth, actual, "change-readonly-disabled"))
    for key, actual in frontend_items.items():
        if key not in truth_items:
            mismatch = "UnexpectedInFrontend"
            if section == "grid_columns":
                mismatch = "UnexpectedFrontendColumn"
            findings.append(_finding(ctx, screen, frontend, backend, section, mismatch, None, actual, "remove-extra-frontend-item"))
            findings.append(_finding(ctx, screen, frontend, backend, section, "FieldKeyMismatch", None, actual, "map-or-remove-field-key"))
            if section == "grid_columns":
                findings.append(_finding(ctx, screen, frontend, backend, section, "GridColumnMismatch", None, actual, "remove-column"))
            elif section == "form_fields":
                findings.append(_finding(ctx, screen, frontend, backend, section, "FormFieldMismatch", None, actual, "remove-field"))
            elif section == "search_filters":
                findings.append(_finding(ctx, screen, frontend, backend, section, "SearchFilterMismatch", None, actual, "remove-filter"))
            elif section == "buttons_actions":
                findings.append(_finding(ctx, screen, frontend, backend, section, "ButtonsActionsMismatch", None, actual, "remove-button"))


def _detect_hidden_exposure(
    ctx: RunContext,
    findings: list[dict[str, Any]],
    screen: dict[str, Any],
    frontend: dict[str, Any],
    backend: dict[str, Any],
) -> None:
    hidden_truth = _by_key((screen.get("sections") or {}).get("hidden_fields") or [])
    visible_frontend: dict[str, dict[str, Any]] = {}
    for section in ("visible_text", "grid_columns", "search_filters", "form_fields", "buttons_actions", "hidden_internal_fields"):
        visible_frontend.update(_by_key([item for item in frontend.get(section) or [] if item.get("visible", True)]))
    for key, truth in hidden_truth.items():
        actual = visible_frontend.get(key)
        if actual is not None:
            findings.append(_finding(ctx, screen, frontend, backend, "hidden_fields", "InternalAuditSystemFieldExposed", truth, actual, "hide-internal-field"))
    for key, actual in _by_key(frontend.get("hidden_internal_fields") or []).items():
        if actual.get("visible") is True:
            findings.append(_finding(ctx, screen, frontend, backend, "hidden_fields", "InternalAuditSystemFieldExposed", hidden_truth.get(key), actual, "hide-internal-field"))


def _finding(
    ctx: RunContext,
    screen: dict[str, Any],
    frontend: dict[str, Any],
    backend: dict[str, Any],
    section: str,
    mismatch_type: str,
    expected: dict[str, Any] | None,
    actual: dict[str, Any] | None,
    suggested_fix: str,
) -> dict[str, Any]:
    expected_value = _item_summary(expected)
    actual_value = _item_summary(actual)
    confidence = _lower_confidence(expected, actual)
    backend_status = _backend_status(backend, (expected or actual or {}).get("key"))
    if backend_status == "conflicts":
        confidence = "low"
    needs = (
        confidence != "high"
        or (expected or {}).get("needs_human_confirmation") is True
        or (actual or {}).get("needs_human_confirmation") is True
        or backend_status == "conflicts"
    )
    frontend_override_forbidden = not ctx.policy.frontend_override_allowed(_aspect(section))
    severity = _severity(mismatch_type)
    source_files = list(screen.get("source_files") or []) + list(frontend.get("source_files") or [])
    key = (expected or actual or {}).get("key", "")
    return {
        "screen_id": screen.get("screen_id") or frontend.get("screen_id") or "",
        "module": ctx.module,
        "field_key": key,
        "mismatch_type": mismatch_type,
        "expected_from_source_of_truth": expected_value,
        "actual_frontend": actual_value,
        "source_files": source_files,
        "confidence": confidence,
        "needs_human_confirmation": needs,
        "severity": severity,
        "suggested_fix_type": suggested_fix,
        "frontend_override_forbidden": frontend_override_forbidden,
        "backend_evidence_agrees_or_conflicts": backend_status,
        "project_memory_read": ctx.memory.read_record.project_memory_read,
        "module_memory_read": ctx.memory.read_record.module_memory_read,
        "handoff_ready_ai_fix_instruction": _instruction(mismatch_type, key, expected_value, actual_value),
        "source": f"compare-contract:{section}",
    }


def _by_key(items: list[Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("key")): item for item in items if isinstance(item, dict) and item.get("key")}


def _item_summary(item: dict[str, Any] | None) -> str:
    if not item:
        return "missing"
    parts = [f"key={item.get('key')}"]
    for field in ("label", "visible", "required", "order", "readonly_disabled"):
        if field in item:
            parts.append(f"{field}={item.get(field)}")
    return ", ".join(parts)


def _lower_confidence(expected: dict[str, Any] | None, actual: dict[str, Any] | None) -> str:
    values = [
        item.get("confidence", "medium")
        for item in (expected, actual)
        if isinstance(item, dict)
    ] or ["medium"]
    return min(values, key=lambda value: CONFIDENCE_RANK.get(value, 1))


def _backend_status(backend: dict[str, Any], key: str | None) -> str:
    if not key:
        return "none"
    backend_keys: set[str] = set()
    for group in backend.get("dto_request_response_fields") or []:
        for field in group.get("fields") or []:
            if isinstance(field, dict) and field.get("key"):
                backend_keys.add(str(field["key"]))
    for mapping in backend.get("field_mapping_evidence") or []:
        if isinstance(mapping, dict):
            backend_keys.update(str(mapping.get(name, "")) for name in ("frontend_key", "backend_key"))
    return "agrees" if key in backend_keys else "none"


def _severity(mismatch_type: str) -> str:
    high = {
        "MissingInFrontend",
        "UnexpectedFrontendColumn",
        "GridColumnMismatch",
        "FieldKeyMismatch",
        "InternalAuditSystemFieldExposed",
        "FrontendOverrideForbidden",
    }
    low = {"OrderMismatch"}
    if mismatch_type in high:
        return "BLOCKER"
    if mismatch_type in low:
        return "MINOR"
    return "MAJOR"


def _instruction(mismatch_type: str, key: str, expected: str, actual: str) -> str:
    return (
        f"Fix frontend field `{key}` for {mismatch_type}: expected source-of-truth `{expected}`, "
        f"actual frontend `{actual}`."
    )


def _aspect(section: str) -> str:
    if section == "grid_columns":
        return "grid_columns"
    if section == "form_fields":
        return "form_fields"
    if section == "search_filters":
        return "search_filters"
    if section == "hidden_fields":
        return "form_fields"
    return "visible_text"
