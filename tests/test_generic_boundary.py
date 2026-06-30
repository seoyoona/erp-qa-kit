from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCANNED_PATHS = [
    ROOT / "erpqa",
    ROOT / "tests",
    ROOT / "README.md",
    ROOT / "pyproject.toml",
]
PUBLIC_DOCS = [
    path
    for path in (ROOT / "docs").glob("*.md")
    if path.name.startswith("generic-erp") or path.name in {"release-checklist.md"}
]
CUSTOMER_TERMS = [
    "ana" + "sa",
    "fe_" + "ana" + "sa",
    "be_" + "ana" + "sa",
    "qc_" + "iqc",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except UnicodeDecodeError:
        return path.read_text(errors="ignore").lower()


class GenericBoundaryTests(unittest.TestCase):
    def test_generic_core_has_no_customer_specific_identifiers(self):
        hits: list[str] = []
        paths: list[Path] = []
        for item in SCANNED_PATHS + PUBLIC_DOCS:
            if item.is_dir():
                paths.extend(
                    path
                    for path in item.rglob("*")
                    if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
                )
            elif item.exists():
                paths.append(item)

        for path in paths:
            rel = path.relative_to(ROOT)
            text = _read_text(path)
            for term in CUSTOMER_TERMS:
                if term in text or term in str(rel).lower():
                    hits.append(f"{rel}: {term}")

        self.assertEqual(hits, [])

    def test_generic_docs_describe_required_quality_commands(self):
        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "README.md",
                "docs/generic-erp-final-qa-evidence-contract.md",
                "docs/generic-erp-qa-operator-runbook.md",
                "docs/generic-erp-qa-scorecard.md",
            ]
            if (ROOT / path).exists()
        )

        for command in ["quality-init", "quality-validate", "quality-impact", "trust-score", "final-qa-signoff"]:
            self.assertIn(command, docs)


if __name__ == "__main__":
    unittest.main()
