from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.cli import main
from erpqa.core.yaml_io import load_yaml
from erpqa.quality.scaffold import QUALITY_SCAFFOLD_FILES
from tests.test_final_qa_gate import write_quality_packet


class QualityCliTests(unittest.TestCase):
    def test_quality_init_scaffolds_all_required_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "qa-context").mkdir()

            exit_code = main(["quality-init", str(project)])

            self.assertEqual(exit_code, 0)
            for rel in QUALITY_SCAFFOLD_FILES:
                self.assertTrue((project / "qa-context" / rel).exists(), rel)

    def test_quality_validate_fails_on_missing_artifacts_with_actionable_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "qa-context").mkdir()

            exit_code = main(["quality-validate", str(project)])

            self.assertEqual(exit_code, 1)

    def test_quality_validate_passes_for_complete_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)

            exit_code = main(["quality-validate", str(project)])

            self.assertEqual(exit_code, 0)

    def test_quality_impact_writes_impact_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)

            exit_code = main([
                "quality-impact",
                str(project),
                "--changed-file",
                "frontend/routes/purchase/orders/page.tsx",
            ])

            self.assertEqual(exit_code, 0)
            data = load_yaml(project / "qa-context" / "quality" / "impact_analysis.yaml")
            self.assertIn("TC-PO-001", data["affected_tests"])

    def test_final_qa_signoff_writes_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_quality_packet(project)

            exit_code = main(["final-qa-signoff", str(project), "--module", "PUR"])

            self.assertEqual(exit_code, 0)
            self.assertTrue((project / "qa-context" / "signoff" / "final_qa_signoff.md").exists())


if __name__ == "__main__":
    unittest.main()
