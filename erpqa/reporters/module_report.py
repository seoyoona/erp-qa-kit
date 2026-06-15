from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.core.context import RunContext
from erpqa.core.errors import ErpqaError
from erpqa.core.module_paths import module_contract_path, write_module_text
from erpqa.core.yaml_io import load_yaml


REQUIRED_FINDING_FIELDS = [
    "screen_id",
    "module",
    "mismatch_type",
    "expected_from_source_of_truth",
    "actual_frontend",
    "source_files",
    "confidence",
    "needs_human_confirmation",
    "severity",
    "suggested_fix_type",
    "frontend_override_forbidden",
    "backend_evidence_agrees_or_conflicts",
    "project_memory_read",
    "module_memory_read",
    "handoff_ready_ai_fix_instruction",
]


def generate_module_reports(ctx: RunContext) -> list[Path]:
    assert ctx.module is not None
    findings_doc = load_yaml(module_contract_path(ctx.project_path, ctx.module, "comparison_findings.yaml"))
    if not isinstance(findings_doc, dict):
        raise ErpqaError(f"comparison findings are missing for module {ctx.module}; run compare-contract first")
    findings = [item for item in findings_doc.get("findings", []) if isinstance(item, dict)]
    paths = [
        write_module_text(ctx.project_path, ctx.module, "reports/screen_frontend_mismatch_report.md", _mismatch_report(ctx, findings)),
        write_module_text(ctx.project_path, ctx.module, "reports/column_mismatch_report.md", _column_report(ctx, findings)),
        write_module_text(ctx.project_path, ctx.module, "reports/frontend_contract_report.md", _frontend_report(ctx)),
        write_module_text(ctx.project_path, ctx.module, "reports/procedure_mapping_report.md", _procedure_report(ctx, findings_doc)),
    ]
    return paths


def _memory_block(ctx: RunContext) -> list[str]:
    return ["## Policy And Memory Read", *[f"- {line}" for line in ctx.memory.read_record.lines()]]


def _mismatch_report(ctx: RunContext, findings: list[dict[str, Any]]) -> str:
    lines = [
        "# Screen Frontend Mismatch Report",
        "",
        "Frontend is the implementation under test. Screen spec plus backend evidence are the source of truth.",
        "",
        *_memory_block(ctx),
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("No mismatches detected at current confidence.")
    for index, finding in enumerate(findings, start=1):
        lines.extend([f"### Finding {index}: {finding.get('mismatch_type')}", ""])
        for field in REQUIRED_FINDING_FIELDS:
            lines.append(f"- {field}: {finding.get(field)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _column_report(ctx: RunContext, findings: list[dict[str, Any]]) -> str:
    column_findings = [
        item
        for item in findings
        if "Column" in str(item.get("mismatch_type")) or item.get("suggested_fix_type") in {"add-column", "remove-column", "reorder-column"}
    ]
    lines = [
        "# Column Mismatch Report",
        "",
        *_memory_block(ctx),
        "",
        "| screen_id | mismatch_type | expected | actual | severity |",
        "|---|---|---|---|---|",
    ]
    if not column_findings:
        lines.append("| - | no column mismatches detected | - | - | - |")
    for item in column_findings:
        lines.append(
            f"| {item.get('screen_id')} | {item.get('mismatch_type')} | {item.get('expected_from_source_of_truth')} | {item.get('actual_frontend')} | {item.get('severity')} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _frontend_report(ctx: RunContext) -> str:
    assert ctx.module is not None
    frontend = load_yaml(module_contract_path(ctx.project_path, ctx.module, "frontend_contract.yaml")) or {}
    lines = [
        "# Frontend Contract Report",
        "",
        *_memory_block(ctx),
        "",
        f"- screen_id: {frontend.get('screen_id')}",
        f"- module: {frontend.get('module')}",
        f"- source_files: {frontend.get('source_files')}",
        "",
        "## Exposed Frontend Items",
    ]
    for section in ("visible_text", "search_filters", "grid_columns", "form_fields", "buttons_actions", "hidden_internal_fields"):
        lines.extend(["", f"### {section}"])
        items = frontend.get(section) or []
        if not items:
            lines.append("- None")
        for item in items:
            lines.append(f"- `{item.get('key')}`: {item.get('label')} visible={item.get('visible')} confidence={item.get('confidence')}")
    return "\n".join(lines).rstrip() + "\n"


def _procedure_report(ctx: RunContext, findings_doc: dict[str, Any]) -> str:
    assert ctx.module is not None
    procedure = load_yaml(module_contract_path(ctx.project_path, ctx.module, "procedure_contract.yaml")) or {}
    lines = [
        "# Procedure Mapping Report",
        "",
        "DEFERRED: procedure/business-logic validation is not authoritative until frontend mismatches are resolved.",
        "",
        *_memory_block(ctx),
        "",
        f"- deferred_steps: {findings_doc.get('deferred', [])}",
        f"- procedure_name: {procedure.get('procedure_name')}",
        f"- procedure_file_path: {procedure.get('procedure_file_path')}",
        f"- parameters: {procedure.get('parameters', [])}",
        f"- result_columns: {procedure.get('result_columns', [])}",
        f"- tables_touched: {procedure.get('tables_touched', [])}",
    ]
    return "\n".join(lines).rstrip() + "\n"
