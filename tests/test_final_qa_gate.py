from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.core.paths import write_yaml
from erpqa.triage.signoff import evaluate_final_qa_gate
from tests.test_final_qa_signoff import complete_trust_evidence
from tests.test_quality_schemas import (
    valid_defect_register,
    valid_environment_fingerprint,
    valid_flake_policy,
    valid_impact_analysis,
    valid_process_catalog,
    valid_test_case_catalog,
    valid_test_data_contract,
    valid_test_run_ledger,
    valid_traceability_matrix,
)


def write_quality_packet(project: Path, omit: str | None = None, residual_count: int = 0) -> None:
    quality = {
        "quality/process_catalog.yaml": valid_process_catalog(),
        "quality/traceability_matrix.yaml": valid_traceability_matrix(),
        "quality/impact_analysis.yaml": valid_impact_analysis(),
        "quality/test_case_catalog.yaml": valid_test_case_catalog(),
        "quality/test_run_ledger.yaml": valid_test_run_ledger(),
        "quality/test_data_contract.yaml": valid_test_data_contract(),
        "quality/defect_register.yaml": valid_defect_register(),
        "quality/environment_fingerprint.yaml": valid_environment_fingerprint(),
        "quality/flake_policy.yaml": valid_flake_policy(),
    }
    quality["quality/test_data_contract.yaml"]["fixtures"][0]["residual_count"] = residual_count
    for rel, data in quality.items():
        if rel == omit:
            continue
        write_yaml(project, rel, data)
    evidence = complete_trust_evidence()
    evidence["findings"] = [{"finding_id": "F-PO-001", "severity": "high", "confidence": "high"}]
    write_yaml(project, "trust_evidence.yaml", evidence)


class FinalQaGateTests(unittest.TestCase):
    def test_final_gate_passes_with_complete_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertTrue(result["pass"], result)
            self.assertGreaterEqual(result["process_coverage"], 0.9)

    def test_final_gate_fails_when_process_catalog_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project, omit="quality/process_catalog.yaml")
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("missing_quality/process_catalog.yaml", result["fail_reasons"])

    def test_final_gate_fails_when_impact_analysis_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project, omit="quality/impact_analysis.yaml")
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("missing_quality/impact_analysis.yaml", result["fail_reasons"])

    def test_final_gate_fails_when_traceability_missing_high_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)
            evidence = complete_trust_evidence()
            evidence["findings"] = [{"finding_id": "F-PO-999", "severity": "medium", "confidence": "high"}]
            write_yaml(project, "trust_evidence.yaml", evidence)
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("unmapped_high_medium_findings", result["fail_reasons"])

    def test_final_gate_fails_when_cleanup_residual_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project, residual_count=1)
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("test_data_contract_failed", result["fail_reasons"])

    def test_final_gate_fails_with_open_confirmed_major_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)
            defect_register = valid_defect_register()
            defect_register["defects"][0].update({"severity": "major", "state": "confirmed"})
            write_yaml(project, "quality/defect_register.yaml", defect_register)
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("defect_gate_failed", result["fail_reasons"])


class FlakePolicyGateTests(unittest.TestCase):
    def test_flake_policy_marks_retry_pass_as_flaky(self):
        from erpqa.quality.flake import apply_flake_policy

        ledger = valid_test_run_ledger()
        ledger["runs"][0]["attempts"] = 2
        result = apply_flake_policy(ledger, valid_flake_policy())
        self.assertEqual(result["flaky_tests"], ["TC-PO-001"])
        self.assertTrue(result["pass"])

    def test_quarantined_impacted_test_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)
            ledger = valid_test_run_ledger()
            ledger["runs"][0]["quarantined"] = True
            ledger["runs"][0]["owner"] = "qa"
            ledger["runs"][0]["reason"] = "unstable browser"
            ledger["runs"][0]["expires_at"] = "2026-07-01"
            write_yaml(project, "quality/test_run_ledger.yaml", ledger)
            result = evaluate_final_qa_gate(project, module="PUR")
            self.assertFalse(result["pass"])
            self.assertIn("flake_policy_failed", result["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
