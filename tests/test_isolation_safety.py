from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.cli import main
from erpqa.safety.approval import approval_allows, normalize_approval
from erpqa.safety.snapshot import (
    collect_file_snapshot,
    compare_file_snapshots,
    write_isolation_snapshot,
)


class IsolationSnapshotTests(unittest.TestCase):
    def test_file_snapshot_detects_changes_outside_allowed_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "extracted").mkdir()
            (root / "qa-context").mkdir()
            (root / "source.txt").write_text("before", encoding="utf-8")
            before = collect_file_snapshot(root, allowed_roots=["extracted", "qa-context"])

            (root / "source.txt").write_text("after", encoding="utf-8")
            after = collect_file_snapshot(root, allowed_roots=["extracted", "qa-context"])

            diff = compare_file_snapshots(before, after)
            self.assertEqual(diff["modified"], ["source.txt"])
            self.assertFalse(diff["pass"])

    def test_file_snapshot_allows_only_qa_context_and_extracted_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa-context").mkdir()
            (root / "extracted").mkdir()
            before = collect_file_snapshot(root, allowed_roots=["extracted", "qa-context"])

            (root / "qa-context" / "report.md").write_text("ok", encoding="utf-8")
            (root / "extracted" / "copy.ts").write_text("copy", encoding="utf-8")
            after = collect_file_snapshot(root, allowed_roots=["extracted", "qa-context"])

            diff = compare_file_snapshots(before, after)
            self.assertTrue(diff["pass"])
            self.assertEqual(diff["unexpected_added"], [])

    def test_write_isolation_snapshot_writes_yaml_under_qa_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa-context").mkdir()
            out = write_isolation_snapshot(root, label="preflight", repos=[])
            self.assertEqual(out.relative_to(root).as_posix(), "qa-context/safety/preflight_snapshot.yaml")
            self.assertTrue(out.exists())


class IsolationSnapshotCliTests(unittest.TestCase):
    def test_isolation_snapshot_and_verify_cli_pass_when_only_allowed_roots_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa-context").mkdir()
            (root / "extracted").mkdir()

            self.assertEqual(main(["isolation-snapshot", str(root), "--label", "preflight"]), 0)
            (root / "qa-context" / "report.md").write_text("ok", encoding="utf-8")
            self.assertEqual(main(["isolation-snapshot", str(root), "--label", "postrun"]), 0)
            self.assertEqual(main(["isolation-verify", str(root), "--before", "preflight", "--after", "postrun"]), 0)

    def test_isolation_verify_cli_fails_when_unallowed_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qa-context").mkdir()
            (root / "source.txt").write_text("before", encoding="utf-8")

            self.assertEqual(main(["isolation-snapshot", str(root), "--label", "preflight"]), 0)
            (root / "source.txt").write_text("after", encoding="utf-8")
            self.assertEqual(main(["isolation-snapshot", str(root), "--label", "postrun"]), 0)
            self.assertEqual(main(["isolation-verify", str(root), "--before", "preflight", "--after", "postrun"]), 1)


class ApprovalLedgerTests(unittest.TestCase):
    def test_read_only_approval_allows_get_only(self):
        approval = normalize_approval({
            "approved_by": "yoona",
            "scope": "erp-demo-read-only",
            "allowed_methods": ["GET"],
            "forbidden_methods": ["POST", "PUT", "PATCH", "DELETE"],
            "expires_at": "2026-06-30T23:59:59+09:00",
        })
        self.assertTrue(approval_allows(approval, method="GET"))
        self.assertFalse(approval_allows(approval, method="POST"))

    def test_write_approval_requires_fixture_and_cleanup(self):
        approval = normalize_approval({
            "approved_by": "yoona",
            "scope": "purchase-disposable-write-uat",
            "allowed_methods": ["POST"],
            "fixture_prefix": "UAT_PO_20260630_",
            "cleanup_required": True,
            "residual_count_required": True,
        })
        self.assertTrue(approval_allows(approval, method="POST", fixture_key="UAT_PO_20260630_001"))
        self.assertFalse(approval_allows(approval, method="POST", fixture_key="REAL_ORDER_001"))


if __name__ == "__main__":
    unittest.main()
