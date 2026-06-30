from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import yaml

from erpqa.cli import main


def complete_trust_evidence() -> dict:
    return {
        "isolation": {
            "pre_snapshot": True,
            "post_snapshot": True,
            "file_diff_pass": True,
            "git_status_unchanged": True,
            "approval_ledger": True,
            "no_live_write_methods": True,
            "no_db_writes": True,
            "artifact_inventory": True,
        },
        "triage": {
            "screen_binding_coverage": 1.0,
            "spec_parser_quality": 0.9,
            "frontend_slice_complete": True,
            "backend_binding_high_confidence": True,
            "confidence_calibrated": True,
            "human_review_queue": True,
            "traceability_coverage": 1.0,
            "impact_analysis_present": True,
            "process_catalog_present": True,
            "unmapped_high_confidence_findings": 0,
        },
        "final_qa": {
            "static_triage_passed": True,
            "browser_smoke_passed": True,
            "readonly_api_passed": True,
            "db_readonly_assertions_passed": True,
            "write_uat_passed": True,
            "cleanup_residual_zero": True,
            "human_signoff_complete": True,
            "process_coverage": 0.95,
            "impacted_test_coverage": 0.96,
            "test_run_ledger_complete": True,
            "defect_gate_passed": True,
            "environment_fingerprint_present": True,
            "test_data_contract_passed": True,
            "flake_policy_applied": True,
        },
    }


class FinalQaSignoffTests(unittest.TestCase):
    def test_trust_score_writes_gate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "qa-context").mkdir()
            (project / "qa-context" / "trust_evidence.yaml").write_text(
                yaml.safe_dump(complete_trust_evidence()), encoding="utf-8"
            )
            self.assertEqual(main(["trust-score", str(project)]), 0)
            self.assertTrue((project / "qa-context" / "reports" / "trust_score.md").exists())
            self.assertTrue((project / "qa-context" / "trust_score.yaml").exists())


class FinalQaReportContentTests(unittest.TestCase):
    def test_final_qa_report_lists_required_evidence(self):
        from erpqa.triage.signoff import render_final_qa_packet

        text = render_final_qa_packet(module="PUR", scores={
            "isolation": {"score": 9.75, "pass": True},
            "triage": {"score": 8.5, "pass": True},
            "final_qa": {"score": 9.0, "pass": True},
        })
        self.assertIn("safety/preflight_snapshot.yaml", text)
        self.assertIn("quality/process_catalog.yaml", text)
        self.assertIn("quality/traceability_matrix.yaml", text)
        self.assertIn("quality/impact_analysis.yaml", text)
        self.assertIn("quality/test_run_ledger.yaml", text)
        self.assertIn("live/write_uat_result.md", text)
        self.assertIn("residual count = 0", text)
        self.assertIn("Open Defects", text)
        self.assertIn("Skipped Or Flaky Tests", text)


if __name__ == "__main__":
    unittest.main()
