from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CONFIDENCE_VALUES, SEVERITY_VALUES, VERIFICATION_TYPES
from .sql_safety import check_sql_safety
from .yaml_io import load_yaml


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    field: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.file}: {self.field}: {self.code}: {self.message}"


ENTITY_FIELDS = [
    "entity",
    "physical_table",
    "module",
    "type",
    "primary_key",
    "important_columns",
    "status_columns",
    "quantity_columns",
    "amount_columns",
    "source",
    "confidence",
    "needs_human_confirmation",
]

FLOW_FIELDS = [
    "flow_id",
    "name",
    "module",
    "steps",
    "trigger_screen",
    "user_action",
    "related_entities",
    "affected_tables",
    "status_transitions",
    "downstream_side_effects",
    "source",
    "confidence",
    "needs_human_confirmation",
]

RULE_FIELDS = [
    "rule_id",
    "name",
    "module",
    "flow",
    "severity",
    "verification_type",
    "description",
    "expected_result",
    "required_entities",
    "required_tables",
    "sql",
    "source",
    "confidence",
    "needs_human_confirmation",
]

FEEDBACK_FIELDS = [
    "feedback_id",
    "title",
    "module",
    "related_flow",
    "related_rule_id",
    "severity",
    "user_observed_behavior",
    "expected_behavior",
    "actual_behavior",
    "reproduction_steps",
    "evidence",
    "affected_records",
    "suspected_area",
    "ai_fix_instruction",
    "validation_after_fix",
    "source",
    "confidence",
    "needs_human_confirmation",
]

LIST_FIELDS = {
    "primary_key",
    "important_columns",
    "status_columns",
    "quantity_columns",
    "amount_columns",
    "steps",
    "related_entities",
    "affected_tables",
    "status_transitions",
    "downstream_side_effects",
    "required_entities",
    "required_tables",
    "reproduction_steps",
}


def _issue(file: Path, field: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(str(file), field, code, message)


def _require_mapping(file: Path, value: Any, root: str) -> list[ValidationIssue]:
    if isinstance(value, dict):
        return []
    return [_issue(file, root, "type", "expected a YAML mapping")]


def _validate_provenance(file: Path, item: dict[str, Any], path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in ("source", "confidence", "needs_human_confirmation"):
        if field not in item:
            issues.append(_issue(file, f"{path}.{field}", "missing", "required provenance field is missing"))

    confidence = item.get("confidence")
    if confidence is not None and confidence not in CONFIDENCE_VALUES:
        issues.append(
            _issue(file, f"{path}.confidence", "enum", "confidence must be one of high, medium, low")
        )

    needs = item.get("needs_human_confirmation")
    if needs is not None and not isinstance(needs, bool):
        issues.append(
            _issue(file, f"{path}.needs_human_confirmation", "type", "needs_human_confirmation must be boolean")
        )
    if confidence in {"low", "medium"} and needs is False:
        issues.append(
            _issue(
                file,
                f"{path}.needs_human_confirmation",
                "human_confirmation",
                "low/medium confidence items must require human confirmation",
            )
        )
    return issues


def _validate_item(
    file: Path,
    item: Any,
    required_fields: list[str],
    path: str,
    enum_checks: dict[str, set[str]] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(item, dict):
        return [_issue(file, path, "type", "expected a mapping")]

    for field in required_fields:
        if field not in item:
            issues.append(_issue(file, f"{path}.{field}", "missing", "required field is missing"))
    for field in LIST_FIELDS & set(required_fields):
        if field in item and not isinstance(item[field], list):
            issues.append(_issue(file, f"{path}.{field}", "type", "expected a list"))
    for field, allowed in (enum_checks or {}).items():
        if field in item and item[field] not in allowed:
            issues.append(_issue(file, f"{path}.{field}", "enum", f"must be one of {', '.join(sorted(allowed))}"))
    issues.extend(_validate_provenance(file, item, path))
    return issues


def _items(data: Any, key: str) -> list[Any]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    return []


def validate_manifest(path: Path) -> list[ValidationIssue]:
    data = load_yaml(path)
    if data is None:
        return [_issue(path, "project_manifest.yaml", "missing_file", "required file is missing")]
    issues = _require_mapping(path, data, "project_manifest")
    if issues:
        return issues
    for field in ("project", "modules", "source_inventory"):
        if field not in data:
            issues.append(_issue(path, field, "missing", "required field is missing"))
    if "project" in data and isinstance(data["project"], dict):
        issues.extend(_validate_provenance(path, data["project"], "project"))
    if "source_inventory" in data and isinstance(data["source_inventory"], list):
        for index, item in enumerate(data["source_inventory"]):
            issues.extend(_validate_provenance(path, item, f"source_inventory[{index}]"))
    return issues


def validate_entity_map(path: Path) -> list[ValidationIssue]:
    data = load_yaml(path)
    if data is None:
        return [_issue(path, "entity_map.yaml", "missing_file", "required file is missing")]
    issues = _require_mapping(path, data, "entity_map")
    if issues:
        return issues
    if "entities" not in data or not isinstance(data.get("entities"), list):
        return [_issue(path, "entities", "missing", "entities list is required")]
    for index, item in enumerate(data["entities"]):
        issues.extend(_validate_item(path, item, ENTITY_FIELDS, f"entities[{index}]"))
    return issues


def validate_flow_map(path: Path) -> list[ValidationIssue]:
    data = load_yaml(path)
    if data is None:
        return [_issue(path, "flow_map.yaml", "missing_file", "required file is missing")]
    issues = _require_mapping(path, data, "flow_map")
    if issues:
        return issues
    if "flows" not in data or not isinstance(data.get("flows"), list):
        return [_issue(path, "flows", "missing", "flows list is required")]
    for index, item in enumerate(data["flows"]):
        issues.extend(_validate_item(path, item, FLOW_FIELDS, f"flows[{index}]"))
    return issues


def validate_rules_file(path: Path) -> list[ValidationIssue]:
    data = load_yaml(path)
    issues = _require_mapping(path, data, "rules")
    if issues:
        return issues
    if "rules" not in data or not isinstance(data.get("rules"), list):
        return [_issue(path, "rules", "missing", "rules list is required")]
    for index, item in enumerate(data["rules"]):
        path_prefix = f"rules[{index}]"
        issues.extend(
            _validate_item(
                path,
                item,
                RULE_FIELDS,
                path_prefix,
                {"severity": SEVERITY_VALUES, "verification_type": VERIFICATION_TYPES},
            )
        )
        if isinstance(item, dict) and item.get("verification_type") == "DB_ASSERTION" and item.get("sql"):
            result = check_sql_safety(item.get("sql"))
            if not result.ok:
                issues.append(_issue(path, f"{path_prefix}.sql", "sql_safety", result.reason))
    return issues


def validate_feedback(path: Path) -> list[ValidationIssue]:
    if not path.exists():
        return []
    data = load_yaml(path)
    issues = _require_mapping(path, data, "feedback_items")
    if issues:
        return issues
    if "feedback_items" not in data or not isinstance(data.get("feedback_items"), list):
        return [_issue(path, "feedback_items", "missing", "feedback_items list is required")]
    for index, item in enumerate(data["feedback_items"]):
        issues.extend(
            _validate_item(
                path,
                item,
                FEEDBACK_FIELDS,
                f"feedback_items[{index}]",
                {"severity": SEVERITY_VALUES},
            )
        )
    return issues


def _load_ids(qa_path: Path) -> tuple[set[str], set[str], set[str], dict[str, str]]:
    entities = load_yaml(qa_path / "entity_map.yaml") or {}
    flows = load_yaml(qa_path / "flow_map.yaml") or {}
    entity_names = {item.get("entity") for item in _items(entities, "entities") if isinstance(item, dict)}
    table_names = {item.get("physical_table") for item in _items(entities, "entities") if isinstance(item, dict)}
    flow_ids = {item.get("flow_id") for item in _items(flows, "flows") if isinstance(item, dict)}
    rules: dict[str, str] = {}
    for file in sorted((qa_path / "rules").glob("*.yaml")):
        data = load_yaml(file) or {}
        for item in _items(data, "rules"):
            if isinstance(item, dict) and item.get("rule_id"):
                rules[item["rule_id"]] = str(file)
    return set(filter(None, entity_names)), set(filter(None, table_names)), set(filter(None, flow_ids)), rules


def _cross_reference_issues(qa_path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    entity_names, table_names, flow_ids, rule_ids = _load_ids(qa_path)
    flow_data = load_yaml(qa_path / "flow_map.yaml") or {}
    for index, flow in enumerate(_items(flow_data, "flows")):
        if not isinstance(flow, dict):
            continue
        for entity in flow.get("related_entities") or []:
            if entity not in entity_names:
                issues.append(_issue(qa_path / "flow_map.yaml", f"flows[{index}].related_entities", "reference", f"unknown entity: {entity}"))

    for file in sorted((qa_path / "rules").glob("*.yaml")):
        data = load_yaml(file) or {}
        for index, rule in enumerate(_items(data, "rules")):
            if not isinstance(rule, dict):
                continue
            if rule.get("flow") and rule["flow"] not in flow_ids:
                issues.append(_issue(file, f"rules[{index}].flow", "reference", f"unknown flow: {rule['flow']}"))
            for entity in rule.get("required_entities") or []:
                if entity not in entity_names:
                    issues.append(_issue(file, f"rules[{index}].required_entities", "reference", f"unknown entity: {entity}"))
            for table in rule.get("required_tables") or []:
                if table not in table_names:
                    issues.append(_issue(file, f"rules[{index}].required_tables", "reference", f"unknown table: {table}"))

    feedback = qa_path / "feedback" / "feedback_items.yaml"
    feedback_data = load_yaml(feedback) or {}
    for index, item in enumerate(_items(feedback_data, "feedback_items")):
        if not isinstance(item, dict):
            continue
        if item.get("related_flow") and item["related_flow"] not in flow_ids:
            issues.append(_issue(feedback, f"feedback_items[{index}].related_flow", "reference", f"unknown flow: {item['related_flow']}"))
        related_rule = item.get("related_rule_id")
        if related_rule and related_rule not in rule_ids:
            issues.append(_issue(feedback, f"feedback_items[{index}].related_rule_id", "reference", f"unknown rule: {related_rule}"))
    return issues


def validate_project(project_path: str | Path) -> list[ValidationIssue]:
    qa_path = Path(project_path).resolve() / "qa-context"
    issues: list[ValidationIssue] = []
    if not qa_path.exists():
        return [_issue(qa_path, "qa-context", "missing_dir", "qa-context is missing; run erpqa init")]

    issues.extend(validate_manifest(qa_path / "project_manifest.yaml"))
    issues.extend(validate_entity_map(qa_path / "entity_map.yaml"))
    issues.extend(validate_flow_map(qa_path / "flow_map.yaml"))
    rules_dir = qa_path / "rules"
    for file in sorted(rules_dir.glob("*.yaml")):
        issues.extend(validate_rules_file(file))
    issues.extend(validate_feedback(qa_path / "feedback" / "feedback_items.yaml"))
    issues.extend(_cross_reference_issues(qa_path))
    return issues

