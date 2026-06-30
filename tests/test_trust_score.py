from __future__ import annotations

import unittest

from erpqa.triage.score import score_final_qa, score_isolation, score_triage


class TrustScoreTests(unittest.TestCase):
    def test_isolation_reaches_95_only_with_hashes_and_no_drift(self):
        score = score_isolation({
            "pre_snapshot": True,
            "post_snapshot": True,
            "file_diff_pass": True,
            "git_status_unchanged": True,
            "approval_ledger": True,
            "no_live_write_methods": True,
            "no_db_writes": True,
            "artifact_inventory": True,
        })
        self.assertGreaterEqual(score["score"], 9.5)

    def test_triage_cannot_reach_8_with_no_available_adapter(self):
        score = score_triage({
            "screen_binding_coverage": 1.0,
            "spec_parser_quality": 0.0,
            "frontend_slice_complete": True,
            "backend_binding_high_confidence": True,
            "confidence_calibrated": True,
            "human_review_queue": True,
            "traceability_coverage": 1.0,
            "impact_analysis_present": True,
            "process_catalog_present": True,
            "unmapped_high_confidence_findings": 0,
        })
        self.assertLess(score["score"], 8.0)

    def test_triage_requires_traceability_and_impact_analysis(self):
        score = score_triage({
            "screen_binding_coverage": 1.0,
            "spec_parser_quality": 0.9,
            "frontend_slice_complete": True,
            "backend_binding_high_confidence": True,
            "confidence_calibrated": True,
            "human_review_queue": True,
            "traceability_coverage": 0.5,
            "impact_analysis_present": False,
            "process_catalog_present": True,
            "unmapped_high_confidence_findings": 1,
        })
        self.assertFalse(score["pass"])

    def test_final_qa_requires_runtime_and_cleanup_evidence(self):
        score = score_final_qa({
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
        })
        self.assertGreaterEqual(score["score"], 9.0)
        self.assertTrue(score["pass"])

    def test_final_qa_fails_when_impacted_tests_are_undercovered(self):
        score = score_final_qa({
            "static_triage_passed": True,
            "browser_smoke_passed": True,
            "readonly_api_passed": True,
            "db_readonly_assertions_passed": True,
            "write_uat_passed": True,
            "cleanup_residual_zero": True,
            "human_signoff_complete": True,
            "process_coverage": 0.95,
            "impacted_test_coverage": 0.80,
            "test_run_ledger_complete": True,
            "defect_gate_passed": True,
            "environment_fingerprint_present": True,
            "test_data_contract_passed": True,
            "flake_policy_applied": True,
        })
        self.assertFalse(score["pass"])


if __name__ == "__main__":
    unittest.main()
