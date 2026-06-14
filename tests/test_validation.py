from pathlib import Path
import tempfile
import unittest

from erpqa.core.validation import (
    validate_entity_map,
    validate_feedback,
    validate_flow_map,
    validate_manifest,
    validate_rules_file,
)
from erpqa.core.yaml_io import dump_yaml


def _write(path: Path, data: object) -> Path:
    path.write_text(dump_yaml(data), encoding="utf-8")
    return path


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_manifest_schema_passes(self):
        path = _write(
            self.tmp_path / "project_manifest.yaml",
            {
                "project": {
                    "name": "demo",
                    "target_root": ".",
                    "source": "test",
                    "confidence": "high",
                    "needs_human_confirmation": False,
                },
                "modules": ["inventory"],
                "source_inventory": [],
                "category_counts": {},
            },
        )
        self.assertEqual(validate_manifest(path), [])

    def test_entity_map_schema_passes(self):
        path = _write(
            self.tmp_path / "entity_map.yaml",
            {
                "entities": [
                    {
                        "entity": "InventoryBalance",
                        "physical_table": "tbl_inventory_balance",
                        "module": "inventory",
                        "type": "master",
                        "primary_key": ["item_id"],
                        "important_columns": ["item_id"],
                        "status_columns": [],
                        "quantity_columns": ["on_hand_qty"],
                        "amount_columns": [],
                        "source": "test",
                        "confidence": "high",
                        "needs_human_confirmation": False,
                    }
                ]
            },
        )
        self.assertEqual(validate_entity_map(path), [])

    def test_flow_map_schema_passes(self):
        path = _write(
            self.tmp_path / "flow_map.yaml",
            {
                "flows": [
                    {
                        "flow_id": "shipment_confirm",
                        "name": "Confirm Shipment",
                        "module": "inventory",
                        "steps": ["Open screen", "Confirm"],
                        "trigger_screen": "shipment",
                        "user_action": "confirm_shipment",
                        "related_entities": ["Shipment"],
                        "affected_tables": ["tbl_shipment"],
                        "status_transitions": ["draft -> confirmed"],
                        "downstream_side_effects": ["stock decreases"],
                        "source": "test",
                        "confidence": "high",
                        "needs_human_confirmation": False,
                    }
                ]
            },
        )
        self.assertEqual(validate_flow_map(path), [])

    def test_rule_schema_passes(self):
        path = _write(
            self.tmp_path / "rules.yaml",
            {
                "rules": [
                    {
                        "rule_id": "inv_no_negative_stock",
                        "name": "Stock not negative",
                        "module": "inventory",
                        "flow": "shipment_confirm",
                        "severity": "BLOCKER",
                        "verification_type": "DB_ASSERTION",
                        "description": "No negative stock.",
                        "expected_result": "Zero rows.",
                        "required_entities": ["InventoryBalance"],
                        "required_tables": ["tbl_inventory_balance"],
                        "sql": "SELECT item_id FROM tbl_inventory_balance WHERE on_hand_qty < 0;",
                        "source": "test",
                        "confidence": "high",
                        "needs_human_confirmation": False,
                    }
                ]
            },
        )
        self.assertEqual(validate_rules_file(path), [])

    def test_feedback_schema_passes(self):
        path = _write(
            self.tmp_path / "feedback_items.yaml",
            {
                "feedback_items": [
                    {
                        "feedback_id": "fb_001",
                        "title": "Shipment cancel did not restore stock",
                        "module": "inventory",
                        "related_flow": "shipment_cancel",
                        "related_rule_id": "inv_shipment_cancel_restores_stock",
                        "severity": "MAJOR",
                        "user_observed_behavior": "Stock stayed reduced.",
                        "expected_behavior": "Stock restored.",
                        "actual_behavior": "Stock unchanged.",
                        "reproduction_steps": ["Confirm shipment", "Cancel shipment"],
                        "evidence": "demo",
                        "affected_records": ["shipment_id=SHIP-1"],
                        "suspected_area": "shipment cancel handler",
                        "ai_fix_instruction": "Record reversing movement.",
                        "validation_after_fix": "Run the related rule.",
                        "source": "test",
                        "confidence": "medium",
                        "needs_human_confirmation": True,
                    }
                ]
            },
        )
        self.assertEqual(validate_feedback(path), [])

    def test_missing_required_field_names_file_and_field(self):
        path = _write(
            self.tmp_path / "entity_map.yaml",
            {
                "entities": [
                    {
                        "physical_table": "tbl_inventory_balance",
                        "module": "inventory",
                        "type": "master",
                        "primary_key": ["item_id"],
                        "important_columns": [],
                        "status_columns": [],
                        "quantity_columns": [],
                        "amount_columns": [],
                        "source": "test",
                        "confidence": "high",
                        "needs_human_confirmation": False,
                    }
                ]
            },
        )
        issues = validate_entity_map(path)
        rendered = "\n".join(issue.render() for issue in issues)
        self.assertIn("entity_map.yaml", rendered)
        self.assertIn("entities[0].entity", rendered)

    def test_invalid_provenance_is_rejected(self):
        path = _write(
            self.tmp_path / "entity_map.yaml",
            {
                "entities": [
                    {
                        "entity": "InventoryBalance",
                        "physical_table": "tbl_inventory_balance",
                        "module": "inventory",
                        "type": "master",
                        "primary_key": ["item_id"],
                        "important_columns": [],
                        "status_columns": [],
                        "quantity_columns": [],
                        "amount_columns": [],
                        "source": "test",
                        "confidence": "very-high",
                        "needs_human_confirmation": False,
                    }
                ]
            },
        )
        self.assertTrue(any(issue.field.endswith("confidence") for issue in validate_entity_map(path)))


if __name__ == "__main__":
    unittest.main()
