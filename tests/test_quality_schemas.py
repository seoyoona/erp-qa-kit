from __future__ import annotations

import unittest

from erpqa.quality._common import list_items
from erpqa.quality.defects import defect_gate_passed, validate_defect_register
from erpqa.quality.environment import validate_environment_fingerprint
from erpqa.quality.execution import validate_test_run_ledger
from erpqa.quality.flake import apply_flake_policy, validate_flake_policy
from erpqa.quality.impact import analyze_change_impact, validate_impact_analysis
from erpqa.quality.policy import QualityPolicy, load_project_quality_policy
from erpqa.quality.process import calculate_process_coverage, validate_process_catalog
from erpqa.quality.test_catalog import validate_test_case_catalog
from erpqa.quality.test_data import validate_test_data_contract
from erpqa.quality.traceability import finding_has_traceability, traceability_coverage, validate_traceability_matrix
from erpqa.safety.approval import approval_allows, normalize_approval
from erpqa.triage.score import score_final_qa


REQUIRED_QUALITY_ARTIFACTS = [
    "process_catalog.yaml",
    "traceability_matrix.yaml",
    "impact_analysis.yaml",
    "test_case_catalog.yaml",
    "test_run_ledger.yaml",
    "test_data_contract.yaml",
    "defect_register.yaml",
    "environment_fingerprint.yaml",
    "flake_policy.yaml",
]


def valid_process_catalog() -> dict:
    return {
        "processes": [
            {
                "process_id": "PROC-PO-001",
                "module": "PUR",
                "name": "Purchase order release flow",
                "owner": "qa-owner",
                "release_scope": "purchase-order",
                "source_root": "/tmp/erpqa/extracted/PUR",
                "steps": [
                    {
                        "step_id": "PUR-ORD-001M",
                        "sequence": 1,
                        "screen_id": "PUR-ORD-001M",
                        "route": "/purchase/orders/new",
                        "api": [{"method": "POST", "path": "/api/purchase/orders"}],
                        "sp": ["usp_purchase_order_list"],
                        "tables": ["purchase_order_header", "purchase_order_line"],
                        "expected_state_change": "draft order becomes submitted order",
                    }
                ],
            }
        ]
    }


def valid_traceability_matrix() -> dict:
    return {
        "links": [
            {
                "trace_id": "TR-PO-001",
                "requirement_id": "REQ-PO-001",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "frontend": {
                    "component": "frontend/routes/purchase/orders/page.tsx",
                    "view_config": "frontend/config/purchase-order-view.yaml",
                    "field_name": "order_qty",
                },
                "backend": {
                    "dto": "backend/dto/PurchaseOrderDto.py",
                    "service": "backend/services/purchase_order.py",
                },
                "api": [{"method": "POST", "path": "/api/purchase/orders"}],
                "sp": ["usp_purchase_order_list"],
                "db_assertion": "db/assertions/purchase_order.sql",
                "artifact_refs": [
                    "frontend/routes/purchase/orders/page.tsx",
                    "frontend/config/purchase-order-view.yaml",
                    "backend/dto/PurchaseOrderDto.py",
                    "backend/services/purchase_order.py",
                    "sql/procedures/usp_purchase_order_list.sql",
                    "db/assertions/purchase_order.sql",
                ],
                "test_case_id": "TC-PO-001",
                "defect_id": "DEF-PO-001",
                "signoff_item": "SO-PO-001",
                "finding_ids": ["F-PO-001"],
            }
        ]
    }


def valid_impact_analysis() -> dict:
    return {
        "change_set": [{"path": "frontend/routes/purchase/orders/page.tsx", "type": "route"}],
        "impact_rules": [{"change_type": "route", "maps_to": ["screen_route", "screen", "process", "test"]}],
        "affected_screens": ["PUR-ORD-001M"],
        "affected_processes": ["PROC-PO-001"],
        "affected_tests": ["TC-PO-001"],
    }


def valid_test_case_catalog() -> dict:
    return {
        "test_cases": [
            {
                "test_case_id": "TC-PO-001",
                "type": "manual",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "risk": "high",
                "fixture_contract": "FX-PO-001",
                "expected_evidence": "manual/po-001.md",
            },
            {
                "test_case_id": "TC-PO-002",
                "type": "browser",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "risk": "medium",
                "fixture_contract": "FX-PO-001",
                "expected_evidence": "browser/po-002.md",
            },
            {
                "test_case_id": "TC-PO-003",
                "type": "api",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "risk": "medium",
                "fixture_contract": "FX-PO-001",
                "expected_evidence": "api/po-003.md",
            },
            {
                "test_case_id": "TC-PO-004",
                "type": "db_readonly",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "risk": "medium",
                "fixture_contract": "FX-PO-001",
                "expected_evidence": "db/po-004.md",
            },
            {
                "test_case_id": "TC-PO-005",
                "type": "write_uat",
                "process_id": "PROC-PO-001",
                "screen_id": "PUR-ORD-001M",
                "risk": "high",
                "fixture_contract": "FX-PO-001",
                "expected_evidence": "live/write_uat_result.md",
            },
        ]
    }


def valid_test_run_ledger() -> dict:
    return {
        "runs": [
            {
                "run_id": "RUN-PO-001",
                "test_case_id": "TC-PO-001",
                "runner": "qa-operator",
                "executed_at": "2026-06-30T10:00:00+09:00",
                "environment": "erpqa-demo",
                "account": "qa-demo-user",
                "fixture": "UAT_PO_20260630_001",
                "evidence": "manual/po-001.md",
                "result": "passed",
            }
        ]
    }


def valid_test_data_contract() -> dict:
    return {
        "fixtures": [
            {
                "fixture_id": "FX-PO-001",
                "prefix": "UAT_PO_20260630_",
                "cleanup_actions": [
                    "DELETE FROM purchase_order_line WHERE key LIKE 'UAT_PO_20260630_%'",
                    "DELETE FROM purchase_order_header WHERE key LIKE 'UAT_PO_20260630_%'",
                ],
                "residual_count": 0,
            }
        ]
    }


def valid_defect_register() -> dict:
    return {
        "defects": [
            {
                "defect_id": "DEF-PO-001",
                "severity": "minor",
                "state": "closed",
                "title": "Column label mismatch",
            }
        ]
    }


def valid_environment_fingerprint() -> dict:
    return {
        "build_id": "build-20260630",
        "frontend_commit": "copy-hash-fe",
        "backend_commit": "copy-hash-be",
        "base_url": "https://erpqa-demo.invalid",
        "db_alias": "DEMO-ERP",
        "browser_device": "chromium-desktop",
        "account_role": "purchase-qa",
    }


def valid_flake_policy() -> dict:
    return {
        "retry_limit": 2,
        "flaky_when": "passes_after_retry",
        "quarantine": {"requires": ["owner", "reason", "expires_at"]},
        "score_penalty": {
            "flaky_impacted_test": 0.25,
            "quarantined_impacted_test": "fail_final_qa",
        },
    }


class QualitySchemaTests(unittest.TestCase):
    def test_required_artifact_list_matches_professional_qa_packet(self):
        self.assertEqual(len(REQUIRED_QUALITY_ARTIFACTS), 9)
        self.assertIn("process_catalog.yaml", REQUIRED_QUALITY_ARTIFACTS)
        self.assertIn("flake_policy.yaml", REQUIRED_QUALITY_ARTIFACTS)

    def test_minimal_professional_qa_artifacts_validate(self):
        validators = [
            validate_process_catalog(valid_process_catalog()),
            validate_traceability_matrix(valid_traceability_matrix()),
            validate_impact_analysis(valid_impact_analysis()),
            validate_test_case_catalog(valid_test_case_catalog()),
            validate_test_run_ledger(valid_test_run_ledger(), valid_test_case_catalog()),
            validate_test_data_contract(valid_test_data_contract()),
            validate_defect_register(valid_defect_register()),
            validate_environment_fingerprint(valid_environment_fingerprint()),
            validate_flake_policy(valid_flake_policy()),
        ]
        for validation in validators:
            self.assertTrue(validation["pass"], validation)
            self.assertEqual(validation["missing"], [])

    def test_process_catalog_rejects_policy_forbidden_source_root(self):
        catalog = valid_process_catalog()
        catalog["processes"][0]["source_root"] = "/live/erp/frontend"
        result = validate_process_catalog(catalog, policy=QualityPolicy(forbidden_source_roots=("/live/erp",)))
        self.assertFalse(result["pass"])
        self.assertIn("processes[0].source_root", result["errors"][0])

    def test_process_catalog_has_no_built_in_customer_roots(self):
        catalog = valid_process_catalog()
        catalog["processes"][0]["source_root"] = "/any/customer/workspace"
        result = validate_process_catalog(catalog)
        self.assertTrue(result["pass"], result)

    def test_process_coverage_requires_mapped_and_executed_tests(self):
        coverage = calculate_process_coverage(
            valid_process_catalog(),
            valid_traceability_matrix(),
            valid_test_run_ledger(),
        )
        self.assertEqual(coverage["process_coverage"], 1.0)
        self.assertEqual(coverage["uncovered_processes"], [])

    def test_process_coverage_fails_when_ledger_missing_execution(self):
        coverage = calculate_process_coverage(
            valid_process_catalog(),
            valid_traceability_matrix(),
            {"runs": []},
        )
        self.assertEqual(coverage["process_coverage"], 0.0)
        self.assertEqual(coverage["uncovered_processes"], ["PROC-PO-001"])

    def test_common_list_items_ignores_non_list_values(self):
        self.assertEqual(list_items({"items": {"bad": True}}, "items"), [])

    def test_process_catalog_reports_step_shape_and_evidence_failures(self):
        catalog = valid_process_catalog()
        catalog["processes"][0]["steps"] = "not-a-list"
        result = validate_process_catalog(catalog)
        self.assertFalse(result["pass"])
        self.assertIn("processes[0].steps", result["missing"])

        catalog = valid_process_catalog()
        catalog["processes"][0]["steps"] = ["not-a-mapping"]
        result = validate_process_catalog(catalog)
        self.assertFalse(result["pass"])
        self.assertIn("processes[0].steps[0] must be a mapping", result["errors"])

        catalog = valid_process_catalog()
        catalog["processes"][0]["steps"] = [{
            "step_id": "enter",
            "sequence": 1,
            "screen_id": "PUR-ORD-001M",
            "expected_state_change": "draft_created",
        }]
        result = validate_process_catalog(catalog)
        self.assertFalse(result["pass"])
        self.assertIn("processes[0].steps[0].api_or_sp_or_tables", result["missing"])

    def test_traceability_reports_bad_links_and_defect_id_mapping(self):
        matrix = valid_traceability_matrix()
        link = matrix["links"][0]
        link.pop("api")
        link.pop("sp")
        link["frontend"] = "frontend/routes/purchase/orders/page.tsx"

        result = validate_traceability_matrix(matrix)

        self.assertFalse(result["pass"])
        self.assertIn("links[0].api_or_sp", result["missing"])
        self.assertIn("links[0].frontend must be a mapping", result["errors"])
        self.assertFalse(finding_has_traceability({}, valid_traceability_matrix()))
        self.assertTrue(finding_has_traceability({"id": "DEF-PO-001"}, valid_traceability_matrix()))

    def test_traceability_coverage_ignores_unidentified_findings(self):
        result = traceability_coverage(
            [{"severity": "high", "confidence": "high"}],
            valid_traceability_matrix(),
        )

        self.assertEqual(result["eligible_findings"], [])
        self.assertEqual(result["unmapped_high_confidence_findings"], [])
        self.assertEqual(result["traceability_coverage"], 0.0)

    def test_defect_lifecycle_gate_reports_invalid_open_and_retest_states(self):
        register = {
            "defects": [
                {"defect_id": "DEF-1", "severity": "major", "state": "confirmed", "title": "Open major"},
                {"defect_id": "DEF-2", "severity": "minor", "state": "fixed", "title": "Needs retest"},
                {"defect_id": "DEF-3", "severity": "minor", "state": "rejected", "title": "Rejected without reason"},
                {"defect_id": "DEF-4", "severity": "minor", "state": "triaged", "title": "Bad state"},
            ]
        }

        validation = validate_defect_register(register)
        gate = defect_gate_passed(register, {"runs": []})

        self.assertFalse(validation["pass"])
        self.assertIn("defects[2].rejection_reason", validation["missing"])
        self.assertIn("defects[3].state unsupported: triaged", validation["errors"])
        self.assertEqual(gate["open_blocker_major"], ["DEF-1"])
        self.assertEqual(gate["needs_retest"], ["DEF-2"])
        self.assertEqual(gate["rejected_without_reason"], ["DEF-3"])

    def test_execution_catalog_and_test_data_negative_paths_are_actionable(self):
        ledger = valid_test_run_ledger()
        ledger["runs"][0]["test_case_id"] = "TC-MISSING"
        ledger_result = validate_test_run_ledger(ledger, valid_test_case_catalog())
        self.assertFalse(ledger_result["pass"])
        self.assertIn("runs[0].test_case_id not found in catalog: TC-MISSING", ledger_result["errors"])

        catalog = {"test_cases": [{"test_case_id": "TC-X", "type": "exploratory"}]}
        catalog_result = validate_test_case_catalog(catalog)
        self.assertFalse(catalog_result["pass"])
        self.assertIn("test_cases[0].type unsupported: exploratory", catalog_result["errors"])

        contract = valid_test_data_contract()
        contract["fixtures"][0].pop("residual_count")
        data_result = validate_test_data_contract(contract)
        self.assertFalse(data_result["pass"])
        self.assertIn("fixtures[0].residual_count", data_result["missing"])

    def test_flake_policy_reports_retry_and_quarantine_failures(self):
        policy = {"retry_limit": 1, "flaky_when": "passes_after_retry", "quarantine": {}, "score_penalty": {}}
        validation = validate_flake_policy(policy)
        self.assertFalse(validation["pass"])
        self.assertIn("flake_policy.quarantine.requires", validation["missing"])
        self.assertIn("flake_policy.score_penalty.flaky_impacted_test", validation["missing"])

        ledger = {
            "runs": [
                {"test_case_id": "TC-1", "attempts": 2, "result": "passed"},
                {"test_case_id": "TC-2", "attempts": 3, "result": "failed", "quarantined": True},
            ]
        }
        gate = apply_flake_policy(ledger, valid_flake_policy())

        self.assertFalse(gate["pass"])
        self.assertEqual(gate["flaky_tests"], ["TC-1"])
        self.assertEqual(gate["quarantined_tests"], ["TC-2"])
        self.assertIn("runs[1].owner required for quarantine", gate["errors"])

    def test_impact_analysis_handles_unknown_and_non_mapping_artifact_refs(self):
        matrix = valid_traceability_matrix()
        link = matrix["links"][0]
        link["frontend"] = "not-a-mapping"
        link["backend"] = "not-a-mapping"
        link["api"] = "/api/purchase/orders"
        link["sp"] = [{"path": "sql/procedures/usp_purchase_order_list.sql"}]

        impact = analyze_change_impact(
            ["misc/readme.txt", "api/purchase/orders.py", "sql/procedures/usp_purchase_order_list.sql"],
            matrix,
            valid_test_case_catalog(),
        )

        self.assertEqual(impact["change_set"][0]["type"], "unknown")
        self.assertIn("TC-PO-001", impact["affected_tests"])
        self.assertTrue(validate_impact_analysis(impact)["pass"])

    def test_quality_policy_defaults_when_project_policy_is_missing(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            policy = load_project_quality_policy(Path(tmp))

        self.assertEqual(policy.forbidden_source_roots, ())
        self.assertEqual(policy.impact_rules, ())

    def test_live_approval_rejects_methods_outside_allow_list(self):
        approval = normalize_approval({
            "approved_by": "qa-lead",
            "scope": "read-only validation",
            "allowed_methods": ["get"],
            "forbidden_methods": [],
        })

        self.assertTrue(approval_allows(approval, "GET"))
        self.assertFalse(approval_allows(approval, "POST", fixture_key="UAT_PO_001"))

    def test_final_qa_score_reports_cleanup_residual_failure(self):
        evidence = {
            "process_coverage": 0.95,
            "impacted_test_coverage": 0.96,
            "test_run_ledger_complete": True,
            "defect_gate_passed": True,
            "environment_fingerprint_present": True,
            "test_data_contract_passed": True,
            "flake_policy_applied": True,
            "cleanup_residual_zero": False,
        }

        score = score_final_qa(evidence)

        self.assertFalse(score["pass"])
        self.assertIn("cleanup_residual_not_zero", score["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
