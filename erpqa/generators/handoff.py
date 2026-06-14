from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.core.errors import ErpqaError
from erpqa.core.paths import ensure_qa_context, write_text, write_text_if_missing, write_yaml_if_missing
from erpqa.core.scaffold import FEEDBACK_ITEMS_STUB, PM_TEMPLATE
from erpqa.core.yaml_io import load_yaml
from erpqa.generators.sql import load_rules


def _items(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    return []


def _rule_map(project_path: Path) -> dict[str, dict[str, Any]]:
    return {str(rule.get("rule_id")): rule for rule in load_rules(project_path)}


def _flow_map(project_path: Path) -> dict[str, dict[str, Any]]:
    data = load_yaml(project_path / "qa-context" / "flow_map.yaml") or {}
    return {str(flow.get("flow_id")): flow for flow in _items(data, "flows")}


def generate_handoff(project_path: str | Path) -> tuple[Path, Path]:
    root = Path(project_path).resolve()
    ensure_qa_context(root)
    qa = root / "qa-context"
    required = [qa / "reports", qa / "rules", qa / "entity_map.yaml", qa / "flow_map.yaml", qa / "feedback"]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ErpqaError("required handoff input is missing: " + ", ".join(str(path) for path in missing))

    write_yaml_if_missing(root, "feedback/feedback_items.yaml", FEEDBACK_ITEMS_STUB)
    write_text_if_missing(root, "feedback/PM_FEEDBACK_TEMPLATE.md", PM_TEMPLATE)

    feedback = _items(load_yaml(qa / "feedback" / "feedback_items.yaml") or {}, "feedback_items")
    rules = _rule_map(root)
    flows = _flow_map(root)

    lines = [
        "# Fix Handoff",
        "",
        "This document is advisory. ERP QA Kit does not modify target ERP code.",
        "",
        "## Agent Capabilities Covered",
        "1. Locate likely affected module/code path.",
        "2. Understand expected vs actual behavior.",
        "3. Inspect related rules and SQL assertions.",
        "4. Implement a fix in the separate target ERP codebase.",
        "5. Add or update tests covering the fix.",
        "6. Rerun validation after the fix.",
        "",
    ]

    if not feedback:
        lines.extend(["## Feedback Items", "", "No structured feedback items are present yet."])
    for item in feedback:
        rule = rules.get(str(item.get("related_rule_id")), {})
        flow = flows.get(str(item.get("related_flow")), {})
        sql_path = qa / "generated" / "sql" / f"{item.get('related_rule_id')}.sql"
        lines.extend(
            [
                f"## {item.get('feedback_id')}: {item.get('title')}",
                "",
                "### 1. Locate likely affected module/code path",
                f"- Module: `{item.get('module')}`",
                f"- Suspected area: {item.get('suspected_area')}",
                f"- Related flow: `{item.get('related_flow')}` - {flow.get('name', 'not found')}",
                "",
                "### 2. Understand expected vs actual behavior",
                f"- Observed: {item.get('user_observed_behavior')}",
                f"- Expected: {item.get('expected_behavior')}",
                f"- Actual: {item.get('actual_behavior')}",
                "",
                "### 3. Inspect related rules and SQL assertions",
                f"- Related rule: `{item.get('related_rule_id')}` - {rule.get('name', 'not found')}",
                f"- Rule expected result: {rule.get('expected_result', 'not found')}",
                f"- SQL assertion: `{sql_path.relative_to(root).as_posix()}`" if sql_path.exists() else "- SQL assertion: not emitted; check generation status.",
                "",
                "### 4. Implement fix in target ERP codebase",
                f"- Instruction: {item.get('ai_fix_instruction')}",
                "- Apply changes only in the target ERP repository during a separate human-approved fix session.",
                "",
                "### 5. Add/update tests",
                "- Add or update tests for the affected code path and data-integrity behavior.",
                "",
                "### 6. Rerun validation after fix",
                f"- {item.get('validation_after_fix')}",
                "",
                "### Reproduction and evidence",
                "- Steps:",
            ]
        )
        for step in item.get("reproduction_steps") or []:
            lines.append(f"  - {step}")
        lines.extend(
            [
                f"- Evidence: {item.get('evidence')}",
                f"- Affected records: {item.get('affected_records')}",
                f"- Source: {item.get('source')}",
                f"- Confidence: `{item.get('confidence')}`",
                f"- Needs human confirmation: `{item.get('needs_human_confirmation')}`",
                "",
            ]
        )

    fix_handoff = write_text(root, "handoff/fix_handoff.md", "\n".join(lines).rstrip() + "\n")

    prompt_lines = [
        "# Codex Fix Prompt",
        "",
        "You are working in the target ERP codebase, not in ERP QA Kit.",
        "Use `qa-context/handoff/fix_handoff.md`, the related rule YAML, and generated SQL assertions as context.",
        "",
        "Required workflow:",
        "1. Locate the likely affected module/code path named in the handoff.",
        "2. Compare expected behavior, actual behavior, and reproduction steps.",
        "3. Inspect the related data-integrity rule and SQL assertion.",
        "4. Implement the smallest correct fix in the target ERP codebase.",
        "5. Add or update tests for the behavior.",
        "6. Rerun the validation named in the handoff and report results.",
        "",
        "Do not edit ERP QA Kit artifacts unless the human explicitly asks.",
    ]
    codex_prompt = write_text(root, "handoff/codex_fix_prompt.md", "\n".join(prompt_lines).rstrip() + "\n")
    return fix_handoff, codex_prompt
