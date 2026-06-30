from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


_RUN_FIELDS = [
    "runner",
    "executed_at",
    "environment",
    "account",
    "fixture",
    "evidence",
    "result",
]


def validate_test_run_ledger(ledger: dict, catalog: dict | None = None) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    runs = list_items(ledger, "runs")
    if not runs:
        missing.append("runs")
    catalog_ids = {
        case.get("test_case_id")
        for case in list_items(catalog or {}, "test_cases")
        if case.get("test_case_id")
    }
    for idx, run in enumerate(runs):
        prefix = f"runs[{idx}]"
        missing.extend(require_fields(run, ["test_case_id", *_RUN_FIELDS], prefix))
        if run.get("result") == "failed" and not run.get("defect_link"):
            missing.append(f"{prefix}.defect_link")
        if catalog_ids and run.get("test_case_id") and run.get("test_case_id") not in catalog_ids:
            errors.append(f"{prefix}.test_case_id not found in catalog: {run.get('test_case_id')}")
    return result(missing, errors)


def impacted_test_coverage(impact_analysis: dict, test_run_ledger: dict) -> dict:
    impacted = set(impact_analysis.get("affected_tests", []) or [])
    executed = {
        run.get("test_case_id")
        for run in list_items(test_run_ledger, "runs")
        if run.get("test_case_id") and run.get("result") in {"passed", "failed", "blocked"}
    }
    covered = sorted(impacted & executed)
    missing = sorted(impacted - executed)
    coverage = round(len(covered) / len(impacted), 2) if impacted else 1.0
    return {
        "impacted_test_coverage": coverage,
        "covered_tests": covered,
        "missing_tests": missing,
        "pass": coverage >= 0.95 and not missing,
    }
