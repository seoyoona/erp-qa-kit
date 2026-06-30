from __future__ import annotations

import unittest

from erpqa.quality.execution import impacted_test_coverage, validate_test_run_ledger
from erpqa.quality.test_catalog import validate_test_case_catalog
from erpqa.quality.test_data import validate_test_data_contract
from tests.test_quality_schemas import (
    valid_impact_analysis,
    valid_test_case_catalog,
    valid_test_data_contract,
    valid_test_run_ledger,
)


class TestRunLedgerTests(unittest.TestCase):
    def test_catalog_supports_required_execution_types(self):
        result = validate_test_case_catalog(valid_test_case_catalog())
        self.assertTrue(result["pass"], result)

    def test_ledger_is_complete_for_impacted_tests(self):
        result = impacted_test_coverage(valid_impact_analysis(), valid_test_run_ledger())
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["impacted_test_coverage"], 1.0)

    def test_ledger_fails_when_impacted_test_missing(self):
        result = impacted_test_coverage(valid_impact_analysis(), {"runs": []})
        self.assertFalse(result["pass"])
        self.assertEqual(result["missing_tests"], ["TC-PO-001"])

    def test_write_uat_requires_cleanup_and_zero_residual(self):
        contract = valid_test_data_contract()
        self.assertTrue(validate_test_data_contract(contract)["pass"])
        contract["fixtures"][0]["residual_count"] = 1
        result = validate_test_data_contract(contract)
        self.assertFalse(result["pass"])
        self.assertIn("residual_count", result["errors"][0])

    def test_failed_ledger_row_requires_defect_link(self):
        ledger = valid_test_run_ledger()
        ledger["runs"][0]["result"] = "failed"
        result = validate_test_run_ledger(ledger, valid_test_case_catalog())
        self.assertFalse(result["pass"])
        self.assertIn("defect_link", result["missing"][0])


if __name__ == "__main__":
    unittest.main()
