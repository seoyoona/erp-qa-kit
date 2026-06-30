from __future__ import annotations


def _score(weighted: list[tuple[float, bool]]) -> float:
    return round(sum(weight for weight, ok in weighted if ok), 2)


def score_isolation(evidence: dict) -> dict:
    weighted = [
        (1.25, bool(evidence.get("pre_snapshot"))),
        (1.25, bool(evidence.get("post_snapshot"))),
        (1.50, bool(evidence.get("file_diff_pass"))),
        (1.25, bool(evidence.get("git_status_unchanged"))),
        (1.00, bool(evidence.get("approval_ledger"))),
        (1.25, bool(evidence.get("no_live_write_methods"))),
        (1.25, bool(evidence.get("no_db_writes"))),
        (1.25, bool(evidence.get("artifact_inventory"))),
    ]
    value = _score(weighted)
    return {"gate": "isolation", "score": min(value, 10.0), "pass": value >= 9.5}


def score_triage(evidence: dict) -> dict:
    weighted = [
        (1.25, float(evidence.get("screen_binding_coverage", 0)) >= 0.95),
        (2.50, float(evidence.get("spec_parser_quality", 0)) >= 0.85),
        (0.75, bool(evidence.get("frontend_slice_complete"))),
        (0.75, bool(evidence.get("backend_binding_high_confidence"))),
        (0.50, bool(evidence.get("confidence_calibrated"))),
        (0.50, bool(evidence.get("human_review_queue"))),
        (1.25, float(evidence.get("traceability_coverage", 0)) >= 0.85),
        (1.00, bool(evidence.get("impact_analysis_present"))),
        (0.50, bool(evidence.get("process_catalog_present"))),
        (1.00, int(evidence.get("unmapped_high_confidence_findings", 0)) == 0),
    ]
    value = _score(weighted)
    return {"gate": "triage", "score": min(value, 10.0), "pass": value >= 8.0}


def _final_qa_fail_reasons(evidence: dict) -> list[str]:
    reasons: list[str] = []
    if float(evidence.get("process_coverage", 0)) < 0.90:
        reasons.append("process_coverage_below_90_percent")
    if float(evidence.get("impacted_test_coverage", 0)) < 0.95:
        reasons.append("impacted_test_coverage_below_95_percent")
    for key in [
        "test_run_ledger_complete",
        "defect_gate_passed",
        "environment_fingerprint_present",
        "test_data_contract_passed",
        "flake_policy_applied",
    ]:
        if not evidence.get(key):
            reasons.append(f"missing_{key}")
    if not evidence.get("cleanup_residual_zero"):
        reasons.append("cleanup_residual_not_zero")
    return reasons


def score_final_qa(evidence: dict) -> dict:
    weighted = [
        (0.75, bool(evidence.get("static_triage_passed"))),
        (0.60, bool(evidence.get("browser_smoke_passed"))),
        (0.60, bool(evidence.get("readonly_api_passed"))),
        (0.60, bool(evidence.get("db_readonly_assertions_passed"))),
        (0.75, bool(evidence.get("write_uat_passed"))),
        (0.75, bool(evidence.get("cleanup_residual_zero"))),
        (0.85, bool(evidence.get("human_signoff_complete"))),
        (1.00, float(evidence.get("process_coverage", 0)) >= 0.90),
        (1.00, float(evidence.get("impacted_test_coverage", 0)) >= 0.95),
        (0.75, bool(evidence.get("test_run_ledger_complete"))),
        (0.75, bool(evidence.get("defect_gate_passed"))),
        (0.50, bool(evidence.get("environment_fingerprint_present"))),
        (0.50, bool(evidence.get("test_data_contract_passed"))),
        (0.60, bool(evidence.get("flake_policy_applied"))),
    ]
    value = _score(weighted)
    fail_reasons = _final_qa_fail_reasons(evidence)
    return {
        "gate": "final_qa",
        "score": min(value, 10.0),
        "pass": value >= 9.0 and not fail_reasons,
        "fail_reasons": fail_reasons,
    }
