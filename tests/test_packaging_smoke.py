from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingSmokeTests(unittest.TestCase):
    def test_pyproject_version_matches_package_version(self):
        import tomllib
        import erpqa

        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(data["project"]["version"], erpqa.__version__)

    @unittest.skipUnless(os.environ.get("ERPQA_RUN_PACKAGING_SMOKE") == "1", "release packaging smoke")
    def test_built_wheel_installs_and_runs_cli_from_clean_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dist_dir = tmp_path / "dist"
            subprocess.run(["uv", "build", "--out-dir", str(dist_dir)], cwd=ROOT, check=True)
            wheels = sorted(dist_dir.glob("erp_qa_kit-*.whl"))
            self.assertEqual(len(wheels), 1, wheels)

            venv_dir = tmp_path / "venv"
            subprocess.run(["uv", "venv", "--seed", str(venv_dir)], check=True)
            python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            subprocess.run([str(python), "-m", "pip", "install", str(wheels[0])], check=True)

            result = subprocess.run(
                [str(python), "-m", "erpqa", "--help"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("quality-validate", result.stdout)
            self.assertIn("final-qa-signoff", result.stdout)


if __name__ == "__main__":
    unittest.main()
