from __future__ import annotations

import unittest

from erpqa.quality.traceability import (
    finding_has_traceability,
    traceability_coverage,
    validate_traceability_matrix,
)
from tests.test_quality_schemas import valid_traceability_matrix


class TraceabilityMatrixTests(unittest.TestCase):
    def test_mapped_finding_is_final_qa_eligible(self):
        finding = {"finding_id": "F-PO-001", "severity": "high", "confidence": "high"}
        matrix = valid_traceability_matrix()
        self.assertTrue(validate_traceability_matrix(matrix)["pass"])
        self.assertTrue(finding_has_traceability(finding, matrix))

    def test_unmapped_high_confidence_finding_is_excluded(self):
        findings = [
            {"finding_id": "F-PO-001", "severity": "high", "confidence": "high"},
            {"finding_id": "F-PO-999", "severity": "medium", "confidence": "high"},
        ]
        result = traceability_coverage(findings, valid_traceability_matrix())
        self.assertEqual(result["eligible_findings"], ["F-PO-001"])
        self.assertEqual(result["unmapped_high_confidence_findings"], ["F-PO-999"])
        self.assertEqual(result["traceability_coverage"], 0.5)

    def test_matrix_requires_view_config_for_screen_column_binding(self):
        matrix = valid_traceability_matrix()
        row = matrix["links"][0]
        self.assertEqual(row["frontend"]["view_config"], "frontend/config/purchase-order-view.yaml")
        self.assertEqual(row["frontend"]["field_name"], "order_qty")
        self.assertTrue(validate_traceability_matrix(matrix)["pass"])


if __name__ == "__main__":
    unittest.main()
