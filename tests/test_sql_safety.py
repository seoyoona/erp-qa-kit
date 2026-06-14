import unittest
from pathlib import Path
import tempfile

from erpqa.core.constants import NEEDS_SCHEMA_CONFIRMATION
from erpqa.core.scaffold import init_project
from erpqa.core.sql_safety import DENY_KEYWORDS, check_sql_safety
from erpqa.core.yaml_io import dump_yaml
from erpqa.generators.sql import generate_sql


class SqlSafetyTests(unittest.TestCase):
    def test_forbidden_keywords_are_rejected_individually(self):
        for keyword in DENY_KEYWORDS:
            with self.subTest(keyword=keyword):
                result = check_sql_safety(
                    f"SELECT item_id FROM tbl_inventory_balance WHERE 1 = 1; {keyword} x"
                )
                self.assertFalse(result.ok)
                self.assertTrue(result.reason)

    def test_multi_statement_is_rejected(self):
        result = check_sql_safety(
            "SELECT item_id FROM tbl_inventory_balance; SELECT warehouse_id FROM tbl_inventory_balance;"
        )
        self.assertFalse(result.ok)
        self.assertIn("multiple", result.reason)

    def test_hidden_statement_comment_is_rejected(self):
        result = check_sql_safety(
            "SELECT item_id FROM tbl_inventory_balance -- hidden\n; DELETE FROM tbl_inventory_balance;"
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.reason)

    def test_valid_select_is_accepted(self):
        result = check_sql_safety(
            """
            SELECT item_id, warehouse_id, on_hand_qty
            FROM tbl_inventory_balance
            WHERE on_hand_qty < 0;
            """
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.normalized_sql.startswith("SELECT"))

    def test_audit_status_columns_are_not_false_positives(self):
        # Identifiers that merely contain a denied keyword as a substring must pass.
        for sql in (
            "SELECT id FROM stock WHERE created_at > updated_at",
            "SELECT id, deleted_at FROM po_line",
            "SELECT qty FROM movement WHERE updated_at IS NULL",
            "SELECT created_by, updated_by FROM audit_log",
        ):
            with self.subTest(sql=sql):
                result = check_sql_safety(sql)
                self.assertTrue(result.ok, result.reason)

    def test_destructive_operations_still_rejected(self):
        for sql in (
            "UPDATE stock SET qty = 0",
            "DELETE FROM stock",
            "DROP TABLE stock",
        ):
            with self.subTest(sql=sql):
                result = check_sql_safety(sql)
                self.assertFalse(result.ok)
                self.assertTrue(result.reason)

    def test_generate_sql_rejects_unsafe_rule_without_emitting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            rule_file = project / "qa-context" / "rules" / "unsafe.yaml"
            rule_file.write_text(
                dump_yaml(
                    {
                        "rules": [
                            {
                                "rule_id": "unsafe_drop",
                                "name": "Unsafe drop",
                                "module": "inventory",
                                "flow": "shipment_confirm",
                                "severity": "BLOCKER",
                                "verification_type": "DB_ASSERTION",
                                "description": "Unsafe test rule.",
                                "expected_result": "Rejected.",
                                "required_entities": [],
                                "required_tables": [],
                                "sql": "SELECT item_id FROM tbl_inventory_balance; DROP TABLE tbl_inventory_balance;",
                                "source": "test",
                                "confidence": "high",
                                "needs_human_confirmation": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            statuses = generate_sql(project)

            self.assertEqual(statuses[0]["status"], "UNSAFE")
            self.assertIn("multiple", statuses[0]["reason"])
            self.assertFalse((project / "qa-context" / "generated" / "sql" / "unsafe_drop.sql").exists())

    def test_generate_sql_marks_missing_sql_as_schema_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init_project(project)
            rule_file = project / "qa-context" / "rules" / "missing_sql.yaml"
            rule_file.write_text(
                dump_yaml(
                    {
                        "rules": [
                            {
                                "rule_id": "needs_schema",
                                "name": "Needs schema",
                                "module": "production",
                                "flow": "production_result_complete",
                                "severity": "MAJOR",
                                "verification_type": "DB_ASSERTION",
                                "description": "Missing SQL test rule.",
                                "expected_result": "Needs schema confirmation.",
                                "required_entities": [],
                                "required_tables": [],
                                "sql": None,
                                "source": "test",
                                "confidence": "low",
                                "needs_human_confirmation": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            statuses = generate_sql(project)

            self.assertEqual(statuses[0]["status"], NEEDS_SCHEMA_CONFIRMATION)
            self.assertFalse((project / "qa-context" / "generated" / "sql" / "needs_schema.sql").exists())


if __name__ == "__main__":
    unittest.main()
