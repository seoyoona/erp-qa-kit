from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import yaml

from erpqa.cli import main
from erpqa.core.context import load_context
from erpqa.core.module_scaffold import init_module
from erpqa.generators.module_contracts import generate_screen_contract
from erpqa.screen.extractors import extract_screen_io_text


FIXTURE = Path("tests/fixtures/generic_screen_io/purchase_order_entry.txt")


class GenericScreenIoParserTests(unittest.TestCase):
    def test_extract_screen_io_text_parses_generic_purchase_order_fixture(self):
        parsed = extract_screen_io_text(FIXTURE)
        self.assertEqual(parsed["screen_id"], "PUR-ORD-001M")
        self.assertEqual(parsed["screen_name"], "Purchase Order Entry")
        self.assertEqual(parsed["buttons_actions"], ["Search", "New", "Save", "Submit", "Approve"])
        self.assertIn("Supplier Code", parsed["search_filters"])
        self.assertIn("Order Date From", parsed["search_filters"])
        self.assertIn("Status", parsed["search_filters"])
        self.assertIn("Item Code", parsed["grid_columns"])
        self.assertIn("Order Qty", parsed["grid_columns"])
        self.assertNotIn("id", parsed["grid_columns"])


class ScreenContractGenerationTests(unittest.TestCase):
    def test_text_screen_io_generates_non_empty_screen_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            spec = project / "extracted" / "PUR" / "spec"
            spec.mkdir(parents=True)
            spec_file = spec / FIXTURE.name
            spec_file.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(main(["policy-init", str(project)]), 0)
            init_module(project, "PUR")

            ctx = load_context(project, "PUR", allow_draft_policy=True)
            out = generate_screen_contract(ctx)
            data = yaml.safe_load(out.read_text(encoding="utf-8"))

            self.assertEqual(data["screen_id"], "PUR-ORD-001M")
            self.assertEqual(data["extraction_method"], "screen_io_text")
            labels = [item["label"] for item in data["sections"]["grid_columns"]]
            self.assertIn("Order Qty", labels)
            self.assertNotEqual(data["source"], "no_available_adapter")


if __name__ == "__main__":
    unittest.main()
