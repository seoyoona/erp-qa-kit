from __future__ import annotations

import unittest

from erpqa.quality.impact import analyze_change_impact
from erpqa.quality.policy import QualityPolicy
from tests.test_quality_schemas import valid_test_case_catalog, valid_traceability_matrix


class GenericImpactRulesTests(unittest.TestCase):
    def test_configured_rules_find_impacted_tests_from_artifact_refs(self):
        policy = QualityPolicy(impact_rules=({
            "change_type": "backend_dto",
            "patterns": ["dto/", "Dto.py"],
            "impacts": ["api", "process", "test"],
        },))

        result = analyze_change_impact(
            ["backend/dto/PurchaseOrderDto.py"],
            valid_traceability_matrix(),
            valid_test_case_catalog(),
            impact_rules=policy.impact_rules,
        )

        self.assertEqual(result["affected_processes"], ["PROC-PO-001"])
        self.assertIn("TC-PO-001", result["affected_tests"])
        self.assertEqual(len(result["affected_tests"]), 5)
        self.assertEqual(result["change_set"][0]["type"], "backend_dto")

    def test_unknown_change_requires_manual_review_without_customer_fallback(self):
        result = analyze_change_impact(
            ["docs/release-notes.md"],
            valid_traceability_matrix(),
            valid_test_case_catalog(),
            impact_rules=(),
        )

        self.assertEqual(result["affected_tests"], [])
        self.assertEqual(result["change_set"][0]["type"], "unknown")
        self.assertEqual(result["impact_rules"][0]["maps_to"], ["manual_review"])


if __name__ == "__main__":
    unittest.main()
