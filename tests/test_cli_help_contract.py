from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from erpqa.cli import main


PUBLIC_COMMANDS = [
    "init",
    "intake",
    "validate",
    "quality-init",
    "quality-validate",
    "quality-impact",
    "isolation-snapshot",
    "isolation-verify",
    "trust-score",
    "final-qa-signoff",
]


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


class CliHelpContractTests(unittest.TestCase):
    def test_help_lists_every_release_command(self):
        code, stdout, stderr = run_cli(["--help"])

        self.assertEqual(code, 0, stderr)
        for command in PUBLIC_COMMANDS:
            self.assertIn(command, stdout)

    def test_version_command_reports_project_version(self):
        code, stdout, stderr = run_cli(["--version"])

        self.assertEqual(code, 0, stderr)
        self.assertRegex(stdout.strip(), r"erpqa \d+\.\d+\.\d+")

    def test_quality_validate_missing_artifacts_prints_actionable_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "qa-context").mkdir()
            code, stdout, stderr = run_cli(["quality-validate", str(project)])

        self.assertEqual(code, 1)
        combined = stdout + stderr
        self.assertIn("Validation failed", combined)
        self.assertIn("qa-context/quality/process_catalog.yaml", combined)
        self.assertIn("Run `erpqa quality-init", combined)


if __name__ == "__main__":
    unittest.main()
