from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.quality._common import list_items, result


DEFAULT_IMPACT_RULES: tuple[dict[str, Any], ...] = (
    {
        "change_type": "view_config",
        "patterns": ["viewconfig", "view-config", "header-config", "config/"],
        "impacts": ["screen_column_layout", "screen", "process", "test"],
    },
    {
        "change_type": "route",
        "patterns": ["routes/", "app/d/", "page.tsx"],
        "impacts": ["screen_route", "screen", "process", "test"],
    },
    {
        "change_type": "api_adapter",
        "patterns": ["adapters/api", "/api/"],
        "impacts": ["api", "process", "test"],
    },
    {
        "change_type": "backend_dto",
        "patterns": ["/dto", "dto.", "dto/"],
        "impacts": ["dto", "api", "process", "test"],
    },
    {
        "change_type": "backend_service",
        "patterns": ["service", "controller"],
        "impacts": ["service", "api", "process", "test"],
    },
    {
        "change_type": "stored_procedure",
        "patterns": [".sql", "procedure"],
        "impacts": ["sp", "db_assertion", "process", "test"],
    },
    {
        "change_type": "schema",
        "patterns": ["schema", "table"],
        "impacts": ["db_assertion", "cleanup", "test"],
    },
)


def _matches(path: str, pattern: str) -> bool:
    return pattern.lower() in path.lower()


def _classify_change(path: str, rules: tuple[dict[str, Any], ...]) -> tuple[str, list[str]]:
    for rule in rules:
        if any(_matches(path, str(pattern)) for pattern in rule.get("patterns", [])):
            return str(rule["change_type"]), list(rule.get("impacts", []))
    return "unknown", ["manual_review"]


def _append_ref(refs: list[str], value: object) -> None:
    if value:
        refs.append(str(value))


def _link_artifact_refs(link: dict) -> set[str]:
    refs: list[str] = []
    for ref in link.get("artifact_refs", []) or []:
        _append_ref(refs, ref)

    frontend = link.get("frontend", {})
    if isinstance(frontend, dict):
        _append_ref(refs, frontend.get("component"))
        _append_ref(refs, frontend.get("view_config"))
        _append_ref(refs, frontend.get("field_name"))

    backend = link.get("backend", {})
    if isinstance(backend, dict):
        _append_ref(refs, backend.get("dto"))
        _append_ref(refs, backend.get("service"))

    _append_ref(refs, link.get("db_assertion"))
    for field in ("api", "sp"):
        value = link.get(field)
        if isinstance(value, list):
            for item in value:
                _append_ref(refs, item.get("path") if isinstance(item, dict) else item)
        else:
            _append_ref(refs, value)
    return {ref for ref in refs if ref}


def _path_matches_link(changed_path: str, link: dict) -> bool:
    changed_name = Path(changed_path).name.lower()
    changed_lower = changed_path.lower()
    for ref in _link_artifact_refs(link):
        ref_lower = ref.lower()
        if changed_lower == ref_lower:
            return True
        if changed_name and changed_name == Path(ref).name.lower():
            return True
        if changed_lower.endswith(ref_lower) or ref_lower.endswith(changed_lower):
            return True
    return False


def analyze_change_impact(
    changed_files: list[str],
    traceability_matrix: dict,
    test_case_catalog: dict,
    impact_rules: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
) -> dict:
    rules = tuple(impact_rules) if impact_rules is not None else DEFAULT_IMPACT_RULES
    change_set = []
    for changed in changed_files:
        change_type, impacts = _classify_change(changed, rules)
        change_set.append({"path": changed, "type": change_type, "impact": impacts})

    links = list_items(traceability_matrix, "links")
    affected_links = [
        link
        for link in links
        if any(_path_matches_link(changed, link) for changed in changed_files)
    ]

    screens = sorted({link.get("screen_id") for link in affected_links if link.get("screen_id")})
    processes = sorted({link.get("process_id") for link in affected_links if link.get("process_id")})
    linked_tests = {link.get("test_case_id") for link in affected_links if link.get("test_case_id")}
    catalog_tests = {
        case.get("test_case_id")
        for case in list_items(test_case_catalog, "test_cases")
        if case.get("process_id") in processes or case.get("screen_id") in screens
    }
    tests = sorted((linked_tests | catalog_tests) - {None})
    return {
        "change_set": change_set,
        "impact_rules": [{"change_type": item["type"], "maps_to": item["impact"]} for item in change_set],
        "affected_screens": screens,
        "affected_processes": processes,
        "affected_tests": tests,
        "coverage_required": bool(tests),
    }


def validate_impact_analysis(impact_analysis: dict) -> dict:
    missing: list[str] = []
    for field in ["change_set", "impact_rules", "affected_screens", "affected_processes", "affected_tests"]:
        if impact_analysis.get(field) in (None, "", []):
            missing.append(field)
    return result(missing, [])
