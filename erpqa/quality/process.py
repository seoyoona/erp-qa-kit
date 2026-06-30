from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result
from erpqa.quality.policy import QualityPolicy


_PROCESS_FIELDS = ["process_id", "module", "steps", "owner", "release_scope"]
_STEP_FIELDS = ["step_id", "sequence", "screen_id", "expected_state_change"]


def validate_process_catalog(catalog: dict, policy: QualityPolicy | None = None) -> dict:
    policy = policy or QualityPolicy()
    missing: list[str] = []
    errors: list[str] = []
    processes = list_items(catalog, "processes")
    if not processes:
        missing.append("processes")
    for idx, process in enumerate(processes):
        prefix = f"processes[{idx}]"
        missing.extend(require_fields(process, _PROCESS_FIELDS, prefix))
        source_root = str(process.get("source_root", ""))
        for forbidden_root in policy.forbidden_source_roots:
            if source_root.startswith(forbidden_root):
                errors.append(f"{prefix}.source_root points at forbidden source root: {source_root}")
        steps = process.get("steps", [])
        if not isinstance(steps, list) or not steps:
            missing.append(f"{prefix}.steps")
            continue
        for step_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"{prefix}.steps[{step_idx}] must be a mapping")
                continue
            missing.extend(require_fields(step, _STEP_FIELDS, f"{prefix}.steps[{step_idx}]"))
            if not (step.get("api") or step.get("sp") or step.get("tables")):
                missing.append(f"{prefix}.steps[{step_idx}].api_or_sp_or_tables")
    return result(missing, errors)


def calculate_process_coverage(process_catalog: dict, traceability_matrix: dict, test_run_ledger: dict) -> dict:
    processes = [p.get("process_id") for p in list_items(process_catalog, "processes") if p.get("process_id")]
    links = list_items(traceability_matrix, "links")
    executed = {
        run.get("test_case_id")
        for run in list_items(test_run_ledger, "runs")
        if run.get("test_case_id") and run.get("result") in {"passed", "failed", "blocked"}
    }
    covered: list[str] = []
    uncovered: list[str] = []
    for process_id in processes:
        linked_tests = {
            link.get("test_case_id")
            for link in links
            if link.get("process_id") == process_id and link.get("test_case_id")
        }
        if linked_tests & executed:
            covered.append(process_id)
        else:
            uncovered.append(process_id)
    coverage = round(len(covered) / len(processes), 2) if processes else 0.0
    return {
        "process_coverage": coverage,
        "covered_processes": covered,
        "uncovered_processes": uncovered,
        "pass": coverage >= 0.90,
    }
