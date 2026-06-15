from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import qa_context_path, write_text_if_missing, write_yaml_if_missing
from .yaml_io import load_yaml


PROJECT_MEMORY_SEED = """# Project Memory — ERP QA Kit Pilot

_Last updated: SEED. Read this before every run._

## Project Overview
- The ERP has 7 modules but only one module has been fully verified so far.

## Repositories & Scope
- There are 3 repositories total, including ORD.
- The full repositories are too large to clone/analyze all at once.
- Module-level extracted folders are preferred.

## Source-of-Truth Rules
- Frontend override is forbidden.
- Screen specification and backend evidence are the source of truth for visible text, labels, columns, search filters, and form fields.
- Frontend is the implementation to validate, not the source of truth.

## Trust Levels
- Backend implementation is not fully trusted yet.
- Stored procedures were provided by the client and may be closer to intended business logic, but integration is not fully verified.

## Validation Order & Deferrals
- Frontend screen contract validation must happen before procedure/business logic validation.
- Procedure/business logic validation is deferred until frontend mismatches are resolved.

## Open Questions
- (Add items here as they arise during dry runs.)

## REVIEW REQUIRED
- Confirm or edit this memory before treating it as project-specific truth.
"""


PROJECT_ASSUMPTIONS_SEED: dict[str, Any] = {
    "assumptions": [
        {
            "assumption_id": "A-001",
            "statement": "Backend implementation is not fully trusted yet.",
            "status": "confirmed",
            "applies_to": "project",
            "source": "seed",
            "confidence": "high",
            "needs_human_confirmation": False,
        },
        {
            "assumption_id": "A-002",
            "statement": "Stored procedures provided by the client reflect the intended business logic.",
            "status": "proposed",
            "applies_to": "project",
            "source": "client_statement",
            "confidence": "medium",
            "needs_human_confirmation": True,
        },
        {
            "assumption_id": "A-003",
            "statement": "Screen specification and backend evidence are the source of truth for visible text, labels, columns, search filters, and form fields.",
            "status": "confirmed",
            "applies_to": "project",
            "source": "seed",
            "confidence": "high",
            "needs_human_confirmation": False,
        },
        {
            "assumption_id": "A-004",
            "statement": "Frontend is the implementation under test and must never be treated as the source of truth (override forbidden).",
            "status": "confirmed",
            "applies_to": "project",
            "source": "seed",
            "confidence": "high",
            "needs_human_confirmation": False,
        },
        {
            "assumption_id": "A-005",
            "statement": "Procedure/business-logic validation is deferred until frontend screen-contract mismatches are resolved.",
            "status": "confirmed",
            "applies_to": "project",
            "source": "seed",
            "confidence": "high",
            "needs_human_confirmation": False,
        },
        {
            "assumption_id": "A-006",
            "statement": "The ORD order-search screen spec is image-only and its field/label contract must be human-confirmed before reporting defects.",
            "status": "proposed",
            "applies_to": "module:ORD",
            "source": "dry_run:2026-06-14",
            "confidence": "medium",
            "needs_human_confirmation": True,
        },
    ]
}


def module_memory_seed(module: str) -> str:
    return f"""# Module Memory — {module}

_Last updated: SEED. Read this AFTER project_memory.md; this file wins on conflict._

## Module Overview
- {module} is a module-scoped extracted folder. No full-repo analysis is required.

## Refinements (adds detail to project memory)
- Source-of-truth rule still holds: screen spec + backend evidence are authoritative for labels/columns/filters/fields.

## Overrides (replaces project memory for this module)
- (Add explicit module overrides here. Each override must name the project rule it replaces.)

## Module Open Questions
- (Add module-specific questions here.)
"""


@dataclass(frozen=True)
class MemoryReadRecord:
    project_memory_path: Path
    module_memory_path: Path | None
    project_memory_read: bool
    module_memory_read: bool
    assumptions_path: Path
    assumptions_count: int
    confirmed_assumptions: int
    proposed_assumptions: int
    needs_human_confirmation_count: int
    module_override_detected: bool
    warnings: tuple[str, ...] = ()

    def lines(self) -> list[str]:
        module = self.module_memory_path.parent.name if self.module_memory_path else None
        lines = [
            f"Memory read: qa-context/project_memory.md (project) {'true' if self.project_memory_read else 'false'}",
        ]
        if module:
            lines.append(
                f"Memory read: qa-context/modules/{module}/module_memory.md (module {module}) {'true' if self.module_memory_read else 'false'}"
            )
        lines.append(
            "Assumptions ledger: "
            f"{self.assumptions_count} entries "
            f"({self.confirmed_assumptions} confirmed, {self.proposed_assumptions} proposed) — "
            f"{self.needs_human_confirmation_count} require human confirmation."
        )
        if self.module_override_detected:
            lines.append("Module memory precedence: module-level override/refinement took precedence where applicable.")
        for warning in self.warnings:
            lines.append(f"WARNING: {warning}")
        return lines


@dataclass(frozen=True)
class EffectiveMemory:
    project_text: str
    module_text: str
    assumptions: list[dict[str, Any]]
    read_record: MemoryReadRecord


def project_memory_path(project_path: str | Path) -> Path:
    return qa_context_path(project_path) / "project_memory.md"


def project_assumptions_path(project_path: str | Path) -> Path:
    return qa_context_path(project_path) / "project_assumptions.yaml"


def module_memory_path(project_path: str | Path, module: str) -> Path:
    return qa_context_path(project_path) / "modules" / module / "module_memory.md"


def scaffold_project_memory(project_path: str | Path) -> tuple[Path, Path]:
    memory = write_text_if_missing(project_path, "project_memory.md", PROJECT_MEMORY_SEED)
    assumptions = write_yaml_if_missing(project_path, "project_assumptions.yaml", PROJECT_ASSUMPTIONS_SEED)
    return memory, assumptions


def scaffold_module_memory(project_path: str | Path, module: str) -> Path:
    return write_text_if_missing(project_path, f"modules/{module}/module_memory.md", module_memory_seed(module))


def load_effective_memory(project_path: str | Path, module: str | None = None) -> EffectiveMemory:
    project_path = Path(project_path)
    project_path_value = project_memory_path(project_path)
    assumptions_path_value = project_assumptions_path(project_path)
    module_path_value = module_memory_path(project_path, module) if module else None
    warnings: list[str] = []

    if project_path_value.exists():
        project_text = project_path_value.read_text(encoding="utf-8")
        project_read = True
    else:
        project_text = ""
        project_read = False
        warnings.append("no project_memory.md found; interpretations remain proposed")

    if assumptions_path_value.exists():
        assumptions_doc = load_yaml(assumptions_path_value) or {}
    else:
        assumptions_doc = {"assumptions": []}
        warnings.append("no project_assumptions.yaml found")
    assumptions = [
        item for item in assumptions_doc.get("assumptions", []) if isinstance(item, dict)
    ] if isinstance(assumptions_doc, dict) else []

    module_text = ""
    module_read = False
    module_override = False
    if module_path_value is not None:
        if module_path_value.exists():
            module_text = module_path_value.read_text(encoding="utf-8")
            module_read = True
            module_override = "## Overrides" in module_text and "OVERRIDE" in module_text.upper()
        else:
            warnings.append(f"no module_memory.md found for module {module}")

    confirmed = sum(1 for item in assumptions if item.get("status") == "confirmed")
    proposed = sum(1 for item in assumptions if item.get("status") == "proposed")
    needs = sum(1 for item in assumptions if item.get("needs_human_confirmation") is True)
    record = MemoryReadRecord(
        project_memory_path=project_path_value,
        module_memory_path=module_path_value,
        project_memory_read=project_read,
        module_memory_read=module_read,
        assumptions_path=assumptions_path_value,
        assumptions_count=len(assumptions),
        confirmed_assumptions=confirmed,
        proposed_assumptions=proposed,
        needs_human_confirmation_count=needs,
        module_override_detected=module_override,
        warnings=tuple(warnings),
    )
    return EffectiveMemory(
        project_text=project_text,
        module_text=module_text,
        assumptions=assumptions,
        read_record=record,
    )
