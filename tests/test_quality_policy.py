from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from erpqa.quality.policy import QualityPolicy, load_quality_policy
from erpqa.quality.process import validate_process_catalog
from tests.test_quality_schemas import valid_process_catalog


class QualityPolicyTests(unittest.TestCase):
    def test_validate_process_catalog_rejects_policy_forbidden_roots(self):
        catalog = valid_process_catalog()
        catalog["processes"][0]["source_root"] = "/live/erp/frontend"
        policy = QualityPolicy(forbidden_source_roots=("/live/erp",))

        result = validate_process_catalog(catalog, policy=policy)

        self.assertFalse(result["pass"])
        self.assertIn(
            "processes[0].source_root points at forbidden source root: /live/erp/frontend",
            result["errors"],
        )

    def test_load_quality_policy_reads_forbidden_roots_and_impact_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality_policy.yaml"
            path.write_text(
                "forbidden_source_roots:\n"
                "  - /live/erp\n"
                "impact_rules:\n"
                "  - change_type: route\n"
                "    patterns: ['routes/', 'page.tsx']\n"
                "    impacts: ['screen_route', 'process', 'test']\n",
                encoding="utf-8",
            )

            policy = load_quality_policy(path)

        self.assertEqual(policy.forbidden_source_roots, ("/live/erp",))
        self.assertEqual(policy.impact_rules[0]["change_type"], "route")


if __name__ == "__main__":
    unittest.main()
