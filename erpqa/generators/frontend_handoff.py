from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.core.context import RunContext
from erpqa.core.errors import ErpqaError
from erpqa.core.module_paths import module_contract_path, write_module_text
from erpqa.core.yaml_io import load_yaml


def generate_frontend_handoff(ctx: RunContext) -> tuple[Path, Path]:
    assert ctx.module is not None
    findings_doc = load_yaml(module_contract_path(ctx.project_path, ctx.module, "comparison_findings.yaml"))
    if not isinstance(findings_doc, dict):
        raise ErpqaError(f"comparison findings are missing for module {ctx.module}; run compare-contract first")
    findings = [item for item in findings_doc.get("findings", []) if isinstance(item, dict)]
    frontend = load_yaml(module_contract_path(ctx.project_path, ctx.module, "frontend_contract.yaml")) or {}
    backend = load_yaml(module_contract_path(ctx.project_path, ctx.module, "backend_contract.yaml")) or {}

    fix_handoff = write_module_text(
        ctx.project_path,
        ctx.module,
        "handoff/frontend_fix_handoff.md",
        _fix_handoff_text(ctx, findings, frontend, backend),
    )
    codex_prompt = write_module_text(
        ctx.project_path,
        ctx.module,
        "handoff/codex_frontend_fix_prompt.md",
        _codex_prompt_text(ctx, findings, frontend, backend),
    )
    return fix_handoff, codex_prompt


def _memory_lines(ctx: RunContext) -> list[str]:
    return [f"- {line}" for line in ctx.memory.read_record.lines()]


def _fix_handoff_text(
    ctx: RunContext,
    findings: list[dict[str, Any]],
    frontend: dict[str, Any],
    backend: dict[str, Any],
) -> str:
    lines = [
        "# Frontend Fix Handoff",
        "",
        "This handoff is advisory. ERP QA Kit performs no auto-modification of target code.",
        "Fixes belong in the TARGET FRONTEND repo, not ERP QA Kit.",
        "",
        "## Policy Reminder",
        "- Frontend override is forbidden where project/module policy says so.",
        "- The frontend must conform to the source-of-truth contract; it must not redefine it.",
        "",
        "## Memory Read",
        *_memory_lines(ctx),
        "",
        "## Likely Frontend Files And Components",
        f"- source_files: {frontend.get('source_files', [])}",
        f"- detected_routes_components: {frontend.get('detected_routes_components', [])}",
        "",
        "## Related API / Backend Evidence",
        f"- endpoints: {backend.get('endpoints', [])}",
        f"- dto_request_response_fields: {backend.get('dto_request_response_fields', [])}",
        f"- field_mapping_evidence: {backend.get('field_mapping_evidence', [])}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("No actionable frontend findings are present yet.")
    for item in findings:
        lines.extend(
            [
                f"### {item.get('screen_id')} / {item.get('field_key')} / {item.get('mismatch_type')}",
                f"- Expected labels / columns / fields: {item.get('expected_from_source_of_truth')}",
                f"- Actual FE findings: {item.get('actual_frontend')}",
                f"- Severity: {item.get('severity')}",
                f"- Backend evidence: {item.get('backend_evidence_agrees_or_conflicts')}",
                f"- Frontend override forbidden: {item.get('frontend_override_forbidden')}",
                f"- AI fix instruction: {item.get('handoff_ready_ai_fix_instruction')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Validation Steps After Fix",
            f"1. `erpqa extract-frontend <project_path> --module {ctx.module}`",
            f"2. `erpqa compare-contract <project_path> --module {ctx.module}`",
            f"3. `erpqa module-report <project_path> --module {ctx.module}`",
            "4. Confirm the finding is cleared before a human approves the frontend change.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _codex_prompt_text(
    ctx: RunContext,
    findings: list[dict[str, Any]],
    frontend: dict[str, Any],
    backend: dict[str, Any],
) -> str:
    lines = [
        "# Codex Frontend Fix Prompt",
        "",
        "You are working in the TARGET FRONTEND repo, never in ERP QA Kit.",
        "Do not modify backend code, stored procedures, databases, or ERP QA Kit artifacts unless a human explicitly asks.",
        "Frontend override is forbidden: make the frontend conform to the source-of-truth contract.",
        "",
        "## Memory Read",
        *_memory_lines(ctx),
        "",
        "## Likely Files / Components",
        f"- source_files: {frontend.get('source_files', [])}",
        f"- detected_routes_components: {frontend.get('detected_routes_components', [])}",
        "",
        "## Backend Evidence",
        f"- endpoints: {backend.get('endpoints', [])}",
        "",
        "## Findings To Investigate",
    ]
    if not findings:
        lines.append("- No actionable frontend findings are present yet.")
    for item in findings:
        lines.append(
            f"- screen `{item.get('screen_id')}`, field `{item.get('field_key')}`: "
            f"expected `{item.get('expected_from_source_of_truth')}`, actual `{item.get('actual_frontend')}`; "
            f"fix type `{item.get('suggested_fix_type')}`; frontend_override_forbidden={item.get('frontend_override_forbidden')}"
        )
    lines.extend(
        [
            "",
            "## Required Workflow",
            f"1. Inspect the likely frontend files/components for module {ctx.module}.",
            "2. Compare expected vs actual values above.",
            "3. Apply the smallest frontend-only fix.",
            "4. Add or update frontend tests if the target repo has tests for this screen.",
            f"5. Re-run `erpqa extract-frontend <project_path> --module {ctx.module}`.",
            f"6. Re-run `erpqa compare-contract <project_path> --module {ctx.module}` and `erpqa module-report <project_path> --module {ctx.module}`.",
            "7. Report results for human approval before merging.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
