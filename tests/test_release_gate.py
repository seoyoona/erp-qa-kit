from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LEAK_PATTERN = "|".join(["ana" + "sa", "fe_" + "ana" + "sa", "be_" + "ana" + "sa", "qc_" + "iqc"])


class ReleaseGateTests(unittest.TestCase):
    def test_ci_workflow_runs_release_grade_commands(self):
        workflow = ROOT / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")

        required = [
            "python -m unittest discover -v",
            "coverage run -m unittest discover",
            "coverage report --fail-under=95",
            f'rg -i "{LEAK_PATTERN}"',
            "uv build",
            "ERPQA_RUN_PACKAGING_SMOKE=1",
            "quality-validate examples/pipe-manufacturing-demo",
            "final-qa-signoff examples/pipe-manufacturing-demo --module DEMO",
            "pip-audit",
        ]
        for command in required:
            self.assertIn(command, text)

    def test_release_docs_exist_and_are_customer_neutral(self):
        docs = [
            ROOT / "CHANGELOG.md",
            ROOT / "docs" / "release-checklist.md",
            ROOT / "docs" / "generic-erp-troubleshooting.md",
            ROOT / "docs" / "generic-erp-qa-scorecard.md",
        ]
        for path in docs:
            self.assertTrue(path.exists(), path)
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("ana" + "sa", text)
            self.assertIn("erp", text)

    def test_readme_has_clean_install_quickstart_and_release_warning(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        required = [
            "pip install",
            "erpqa --help",
            "quality-init",
            "quality-validate",
            "final-qa-signoff",
            "approval-gated",
            "pipe-manufacturing-demo",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_release_checklist_contains_exact_release_commands(self):
        text = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

        required = [
            "uv run ruff check erpqa tests",
            "uv run python -m unittest discover -v",
            "uv run coverage report --fail-under=95",
            "uv build",
            "ERPQA_RUN_PACKAGING_SMOKE=1 uv run python -m unittest tests.test_packaging_smoke -v",
            "git tag",
        ]
        for command in required:
            self.assertIn(command, text)

    def test_source_distribution_manifest_includes_public_docs_and_demo_only(self):
        text = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        required = [
            "include CHANGELOG.md",
            "include docs/*.md",
            "recursive-include examples",
        ]
        for entry in required:
            self.assertIn(entry, text)
        self.assertNotIn("recursive-include docs", text)


if __name__ == "__main__":
    unittest.main()
