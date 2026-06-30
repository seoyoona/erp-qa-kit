from __future__ import annotations

import unittest

from erpqa.quality.impact import analyze_change_impact, validate_impact_analysis
from tests.test_quality_schemas import valid_test_case_catalog, valid_traceability_matrix


class ImpactAnalysisTests(unittest.TestCase):
    def test_changed_frontend_api_sp_and_schema_resolve_to_tests(self):
        impact = analyze_change_impact(
            [
                "frontend/routes/purchase/orders/page.tsx",
                "frontend/config/purchase-order-view.yaml",
                "backend/dto/PurchaseOrderDto.py",
                "backend/services/purchase_order.py",
                "sql/procedures/usp_purchase_order_list.sql",
                "db/assertions/purchase_order.sql",
            ],
            valid_traceability_matrix(),
            valid_test_case_catalog(),
        )
        self.assertIn("PUR-ORD-001M", impact["affected_screens"])
        self.assertIn("PROC-PO-001", impact["affected_processes"])
        self.assertIn("TC-PO-001", impact["affected_tests"])
        self.assertTrue(validate_impact_analysis(impact)["pass"])

    def test_view_config_change_is_classified_as_screen_layout_impact(self):
        impact = analyze_change_impact(
            ["frontend/config/purchase-order-view.yaml"],
            valid_traceability_matrix(),
            valid_test_case_catalog(),
        )
        self.assertEqual(impact["change_set"][0]["type"], "view_config")
        self.assertIn("screen_column_layout", impact["change_set"][0]["impact"])


if __name__ == "__main__":
    unittest.main()
