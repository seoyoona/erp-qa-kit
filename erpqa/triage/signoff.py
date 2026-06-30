from __future__ import annotations

from pathlib import Path

from erpqa.core.paths import write_text, write_yaml
from erpqa.core.yaml_io import load_yaml
from erpqa.quality.defects import defect_gate_passed
from erpqa.quality.execution import impacted_test_coverage
from erpqa.quality.flake import apply_flake_policy
from erpqa.quality.process import calculate_process_coverage
from erpqa.quality.traceability import traceability_coverage
from erpqa.quality.validator import load_quality_artifacts, validate_quality_packet
from erpqa.triage.score import score_final_qa, score_isolation, score_triage


def generate_trust_score(project_path: str | Path) -> tuple[Path, Path, dict]:
    evidence = load_yaml(Path(project_path) / "qa-context" / "trust_evidence.yaml") or {}
    scores = {
        "isolation": score_isolation(evidence.get("isolation", {})),
        "triage": score_triage(evidence.get("triage", {})),
        "final_qa": score_final_qa(evidence.get("final_qa", {})),
    }
    yaml_path = write_yaml(project_path, "trust_score.yaml", scores)
    lines = ["# ERP QA Trust Score", ""]
    for name, score in scores.items():
        mark = "PASS" if score["pass"] else "FAIL"
        lines.append(f"- {name}: {score['score']}/10 - {mark}")
    report_path = write_text(project_path, "reports/trust_score.md", "\n".join(lines) + "\n")
    return yaml_path, report_path, scores


def evaluate_final_qa_gate(project_path: str | Path, module: str | None = None) -> dict:
    project = Path(project_path)
    evidence = load_yaml(project / "qa-context" / "trust_evidence.yaml") or {}
    validation = validate_quality_packet(project)
    quality, _ = load_quality_artifacts(project)
    fail_reasons = list(validation["fail_reasons"])
    ledger_valid = validation["checks"]["test_run_ledger"]
    data_valid = validation["checks"]["test_data_contract"]
    env_valid = validation["checks"]["environment_fingerprint"]
    flake_valid = validation["checks"]["flake_policy"]

    process_cov = calculate_process_coverage(
        quality["process_catalog"], quality["traceability_matrix"], quality["test_run_ledger"]
    )
    trace_cov = traceability_coverage(evidence.get("findings", []), quality["traceability_matrix"])
    impact_cov = impacted_test_coverage(quality["impact_analysis"], quality["test_run_ledger"])
    defect_gate = defect_gate_passed(quality["defect_register"], quality["test_run_ledger"])
    flake_gate = apply_flake_policy(quality["test_run_ledger"], quality["flake_policy"])

    if process_cov["process_coverage"] < 0.90:
        fail_reasons.append("process_coverage_below_90_percent")
    if trace_cov["unmapped_high_confidence_findings"]:
        fail_reasons.append("unmapped_high_medium_findings")
    if impact_cov["impacted_test_coverage"] < 0.95:
        fail_reasons.append("impacted_test_coverage_below_95_percent")
    if not defect_gate["pass"]:
        fail_reasons.append("defect_gate_failed")
    if not flake_gate["pass"]:
        fail_reasons.append("flake_policy_failed")

    final_evidence = dict(evidence.get("final_qa", {}))
    final_evidence.update({
        "process_coverage": process_cov["process_coverage"],
        "impacted_test_coverage": impact_cov["impacted_test_coverage"],
        "test_run_ledger_complete": ledger_valid["pass"],
        "defect_gate_passed": defect_gate["pass"],
        "environment_fingerprint_present": env_valid["pass"],
        "test_data_contract_passed": data_valid["pass"],
        "flake_policy_applied": flake_valid["pass"] and flake_gate["pass"],
    })
    score = score_final_qa(final_evidence)
    fail_reasons.extend(reason for reason in score.get("fail_reasons", []) if reason not in fail_reasons)
    fail_reasons = sorted(set(fail_reasons))
    result = {
        "module": module,
        "process_coverage": process_cov["process_coverage"],
        "impact_coverage": impact_cov["impacted_test_coverage"],
        "traceability_coverage": trace_cov["traceability_coverage"],
        "impacted_test_coverage": impact_cov["impacted_test_coverage"],
        "test_run_ledger_complete": ledger_valid["pass"],
        "defect_gate_passed": defect_gate["pass"],
        "environment_fingerprint_present": env_valid["pass"],
        "test_data_contract_passed": data_valid["pass"],
        "flake_policy_applied": flake_valid["pass"] and flake_gate["pass"],
        "human_signoff_complete": bool(final_evidence.get("human_signoff_complete")),
        "open_blocker_major_defects": defect_gate["open_blocker_major"],
        "needs_retest_defects": defect_gate["needs_retest"],
        "skipped_tests": flake_gate.get("skipped_tests", []),
        "flaky_tests": flake_gate["flaky_tests"],
        "quarantined_tests": flake_gate["quarantined_tests"],
        "unmapped_high_confidence_findings": trace_cov["unmapped_high_confidence_findings"],
        "uncovered_processes": process_cov["uncovered_processes"],
        "unexecuted_impacted_tests": impact_cov["missing_tests"],
        "fail_reasons": fail_reasons,
        "score": score,
    }
    result["pass"] = not fail_reasons and score["pass"]
    return result


def render_final_qa_packet(module: str, scores: dict) -> str:
    return f"""# Final ERP QA Sign-off Packet - {module}

## Scores
- Isolation / safety: {scores['isolation']['score']}/10
- First-pass triage: {scores['triage']['score']}/10
- Final ERP QA readiness: {scores['final_qa']['score']}/10

## Required Evidence
- safety/preflight_snapshot.yaml
- safety/postrun_snapshot.yaml
- quality/process_catalog.yaml
- quality/traceability_matrix.yaml
- quality/impact_analysis.yaml
- quality/test_case_catalog.yaml
- quality/test_run_ledger.yaml
- quality/test_data_contract.yaml
- quality/defect_register.yaml
- quality/environment_fingerprint.yaml
- quality/flake_policy.yaml
- modules/{module}/screens/_summary.yaml
- reports/trust_score.md
- live/read_only_check.md
- live/browser_smoke.md
- live/db_readonly_assertions.md
- live/write_uat_plan.md
- live/write_uat_result.md
- live/cleanup_result.md
- live/residual_check.md

## Process, Impact, And Traceability Coverage
- Process coverage must be >= 90%.
- Impacted test coverage must be >= 95%.
- High/medium findings must be mapped in the traceability matrix.

## Open Defects
Confirmed blocker or major defects must be closed or rejected before final QA 9+.

## Skipped Or Flaky Tests
Skipped, flaky, and quarantined tests are listed with score impact and owner.

## Mutation Cleanup Rule
Controlled write UAT is valid only when fixture keys are disposable and residual count = 0.
"""


def write_final_qa_signoff(project_path: str | Path, module: str) -> tuple[Path, dict]:
    scores = generate_trust_score(project_path)[2]
    gate = evaluate_final_qa_gate(project_path, module=module)
    text = render_final_qa_packet(module, scores)
    text += "\n## Gate Result\n"
    text += f"- Pass: {gate['pass']}\n"
    text += f"- Fail reasons: {', '.join(gate['fail_reasons']) if gate['fail_reasons'] else 'none'}\n"
    text += f"- Process coverage: {gate['process_coverage']}\n"
    text += f"- Impacted test coverage: {gate['impacted_test_coverage']}\n"
    text += f"- Traceability coverage: {gate['traceability_coverage']}\n"
    path = write_text(project_path, "signoff/final_qa_signoff.md", text)
    return path, gate
