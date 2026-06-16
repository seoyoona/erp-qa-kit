from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from erpqa.screen.audit import _clean_key, _DYNAMIC_COL_RE
from erpqa.screen.extractors import (
    _role_from_proc,
    extract_frontend_feature,
    extract_spec_screen,
)


class CleanKeyTests(unittest.TestCase):
    def test_alias_exact_then_case_insensitive(self):
        alias = {"iInQty": "in_qty"}
        alias_ci = {k.lower(): v for k, v in alias.items()}
        self.assertEqual(_clean_key("iInQty", alias, alias_ci), "in_qty")
        # spec wrote IYMF (uppercase) but backend alias is iYMF -> case-insensitive bridge
        self.assertEqual(_clean_key("IYMF", {}, {"iymf": "ym_from"}), "ym_from")

    def test_heuristic_strip_leading_i_any_case(self):
        self.assertEqual(_clean_key("iInYmd", {}, {}), "in_ymd")
        # IYM -> strip leading I -> "YM" -> "y_m"; matches FE "ym" via _fe_has flattening.
        self.assertEqual(_clean_key("IYM", {}, {}), "y_m")

    def test_dynamic_column_pattern(self):
        self.assertTrue(_DYNAMIC_COL_RE.match("spec13"))
        self.assertTrue(_DYNAMIC_COL_RE.match("day01"))
        self.assertFalse(_DYNAMIC_COL_RE.match("in_qty"))


class RoleTests(unittest.TestCase):
    def test_role_from_proc(self):
        self.assertEqual(_role_from_proc("MISPD.dbo.str_PDMaterialInput_IU"), "IU")
        self.assertEqual(_role_from_proc("str_PDMaterialInput_S"), "S")
        self.assertEqual(_role_from_proc("str_PDMaterialInput_D_20251217"), "D")


class FrontendExtractTests(unittest.TestCase):
    def test_classifies_filter_and_column_schemas(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "model.ts"
            f.write_text(
                "export const zFooQueryParamsSchema = z.object({\n"
                "  plan_ym: z.string(),\n  item_no: z.string(),\n});\n"
                "export const zFooItemSchema = z.object({\n"
                "  in_qty: z.number(),\n  lot_no: z.string(),\n});\n",
                encoding="utf-8",
            )
            fe = extract_frontend_feature([f])
            self.assertIn("plan_ym", fe.filter_fields)
            self.assertIn("item_no", fe.filter_fields)
            self.assertIn("in_qty", fe.column_fields)
            self.assertNotIn("in_qty", fe.filter_fields)


class SpecExtractTests(unittest.TestCase):
    def test_extracts_sp_params_and_roles(self):
        from openpyxl import Workbook

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PDT-OSC-001M_demo.xlsx"
            wb = Workbook()
            ws = wb.active
            ws["A1"] = "화면 ID"
            ws["B1"] = "PDT-OSC-001M"
            ws["A3"] = "exec MISPD.dbo.str_Demo_IU @iInYmd='20250101',@iInQty=10,@iLotNo='L1'"
            ws["A4"] = "exec MISPD.dbo.str_Demo_S @iPlanYm='202501'"
            wb.save(path)
            spec = extract_spec_screen(path, "PDT-OSC-001M")
            self.assertEqual(spec.params_for_role("IU"), ["iInYmd", "iInQty", "iLotNo"])
            self.assertEqual(spec.params_for_role("S"), ["iPlanYm"])


if __name__ == "__main__":
    unittest.main()
