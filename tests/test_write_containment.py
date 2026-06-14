from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.cli import main
from erpqa.core.errors import WriteOutsideQaContextError
from erpqa.core.paths import qa_output_path

from tests.helpers import copy_demo, snapshot_outside_qa


class WriteContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pipeline_does_not_write_outside_qa_context(self):
        project = copy_demo(self.tmp_path)
        before = snapshot_outside_qa(project)
        for command in ("init", "intake", "validate", "generate-sql", "report", "handoff"):
            self.assertEqual(main([command, str(project)]), 0)
        after = snapshot_outside_qa(project)
        self.assertEqual(after, before)

    def test_write_outside_qa_context_is_rejected(self):
        project = self.tmp_path / "target"
        project.mkdir()
        outside = project / ".." / "outside.txt"
        with self.assertRaises(WriteOutsideQaContextError):
            qa_output_path(project, outside)


if __name__ == "__main__":
    unittest.main()

