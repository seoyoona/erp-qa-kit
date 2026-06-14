from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from erpqa.core.constants import CONFIDENCE_VALUES, SEVERITY_VALUES, VERIFICATION_TYPES
from erpqa.core.errors import ErpqaError
from erpqa.core.paths import ensure_qa_context, write_text
from erpqa.core.yaml_io import load_yaml
from erpqa.generators.sql import load_rules


def _list(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def _generation_statuses(project_path: Path) -> dict[str, str]:
    data = load_yaml(project_path / "qa-context" / "generated" / "sql" / "generation_status.yaml") or {}
    return {row.get("rule_id"): row.get("status") for row in data.get("sql_generation", []) if isinstance(row, dict)}


def _human_confirmation_items(label: str, items: list[dict[str, Any]], id_field: str) -> list[str]:
    lines: list[str] = []
    for item in items:
        if item.get("needs_human_confirmation") is True or item.get("confidence") == "low":
            identifier = item.get(id_field) or item.get("name") or "unknown"
            lines.append(
                f"- {label}: `{identifier}` | confidence: `{item.get('confidence')}` | source: {item.get('source')}"
            )
    return lines


def generate_report(project_path: str | Path) -> Path:
    root = Path(project_path).resolve()
    ensure_qa_context(root)
    qa = root / "qa-context"
    required = [qa / "entity_map.yaml", qa / "flow_map.yaml", qa / "rules"]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ErpqaError("required report input is missing: " + ", ".join(str(path) for path in missing))

    entities = _list(load_yaml(qa / "entity_map.yaml") or {}, "entities")
    flows = _list(load_yaml(qa / "flow_map.yaml") or {}, "flows")
    rules = load_rules(root)
    feedback = _list(load_yaml(qa / "feedback" / "feedback_items.yaml") or {}, "feedback_items")
    statuses = _generation_statuses(root)

    severity_counts = Counter(str(rule.get("severity")) for rule in rules)
    verification_counts = Counter(str(rule.get("verification_type")) for rule in rules)
    confidence_counts = Counter(
        str(item.get("confidence"))
        for collection in (entities, flows, rules, feedback)
        for item in collection
        if item.get("confidence")
    )

    lines = [
        "# ERP QA Report",
        "",
        "This report is deterministic and advisory. Humans approve business meaning, severity, and release decisions.",
        "",
        "## Entities Summary",
        f"- Total entities: {len(entities)}",
    ]
    for entity in entities:
        lines.append(f"- `{entity.get('entity')}` -> `{entity.get('physical_table')}` ({entity.get('module')})")

    lines.extend(["", "## Flows Summary", f"- Total flows: {len(flows)}"])
    for flow in flows:
        lines.append(f"- `{flow.get('flow_id')}`: {flow.get('name')} ({flow.get('module')})")

    lines.extend(["", "## Rules Summary", f"- Total rules: {len(rules)}"])
    for rule in rules:
        status = statuses.get(str(rule.get("rule_id")), "not generated")
        lines.append(
            f"- `{rule.get('rule_id')}` | severity: `{rule.get('severity')}` | "
            f"type: `{rule.get('verification_type')}` | SQL status: `{status}`"
        )

    lines.extend(["", "## Severity Breakdown"])
    for severity in sorted(SEVERITY_VALUES):
        lines.append(f"- {severity}: {severity_counts.get(severity, 0)}")

    lines.extend(["", "## Verification Type Breakdown"])
    for verification_type in sorted(VERIFICATION_TYPES):
        lines.append(f"- {verification_type}: {verification_counts.get(verification_type, 0)}")

    lines.extend(["", "## Confidence Breakdown"])
    lines.append("_Counts aggregate across entities, flows, rules, and feedback items._")
    for confidence in sorted(CONFIDENCE_VALUES):
        lines.append(f"- {confidence}: {confidence_counts.get(confidence, 0)}")

    lines.extend(["", "## SQL Generation Status"])
    if statuses:
        for rule_id, status in sorted(statuses.items()):
            lines.append(f"- `{rule_id}`: `{status}`")
    else:
        lines.append("- No SQL generation status found. Run `erpqa generate-sql` first.")

    lines.extend(["", "## Needs Human Confirmation"])
    human_lines: list[str] = []
    human_lines.extend(_human_confirmation_items("entity", entities, "entity"))
    human_lines.extend(_human_confirmation_items("flow", flows, "flow_id"))
    human_lines.extend(_human_confirmation_items("rule", rules, "rule_id"))
    human_lines.extend(_human_confirmation_items("feedback", feedback, "feedback_id"))
    lines.extend(human_lines or ["- None recorded."])

    return write_text(root, "reports/qa_report.md", "\n".join(lines).rstrip() + "\n")
