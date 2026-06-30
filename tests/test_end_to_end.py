from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.cli import main

from tests.helpers import copy_demo


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_demo_pipeline_produces_expected_artifacts(self):
        project = copy_demo(self.tmp_path)
        for command in ("init", "intake", "validate", "generate-sql", "report", "handoff"):
            self.assertEqual(main([command, str(project)]), 0, command)

        qa = project / "qa-context"
        expected = [
            qa / "project_manifest.yaml",
            qa / "source_inventory.md",
            qa / "entity_map.yaml",
            qa / "flow_map.yaml",
            qa / "rules" / "pipe_manufacturing_rules.yaml",
            qa / "reports" / "qa_report.md",
            qa / "handoff" / "fix_handoff.md",
            qa / "handoff" / "codex_fix_prompt.md",
            qa / "feedback" / "feedback_items.yaml",
            qa / "feedback" / "PM_FEEDBACK_TEMPLATE.md",
        ]
        for path in expected:
            self.assertTrue(path.exists(), path)
        self.assertTrue(list((qa / "generated" / "sql").glob("*.sql")))
        self.assertIn(
            "NEEDS_SCHEMA_CONFIRMATION",
            (qa / "generated" / "sql" / "generation_status.yaml").read_text(),
        )

    def test_pipe_manufacturing_demo_quality_packet_validates(self):
        project = copy_demo(self.tmp_path)

        exit_code = main(["quality-validate", str(project)])

        self.assertEqual(exit_code, 0)

    def test_pipe_manufacturing_demo_final_signoff_scores_9_8_plus(self):
        project = copy_demo(self.tmp_path)

        exit_code = main(["final-qa-signoff", str(project), "--module", "DEMO"])

        self.assertEqual(exit_code, 0)
        signoff = project / "qa-context" / "signoff" / "final_qa_signoff.md"
        self.assertTrue(signoff.exists())


if __name__ == "__main__":
    unittest.main()
