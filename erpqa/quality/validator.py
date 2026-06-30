from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.core.yaml_io import load_yaml
from erpqa.quality.defects import validate_defect_register
from erpqa.quality.environment import validate_environment_fingerprint
from erpqa.quality.execution import validate_test_run_ledger
from erpqa.quality.flake import validate_flake_policy
from erpqa.quality.impact import validate_impact_analysis
from erpqa.quality.policy import QualityPolicy, load_project_quality_policy
from erpqa.quality.process import validate_process_catalog
from erpqa.quality.test_catalog import validate_test_case_catalog
from erpqa.quality.test_data import validate_test_data_contract
from erpqa.quality.traceability import validate_traceability_matrix


QUALITY_FILES = {
    "process_catalog": "quality/process_catalog.yaml",
    "traceability_matrix": "quality/traceability_matrix.yaml",
    "impact_analysis": "quality/impact_analysis.yaml",
    "test_case_catalog": "quality/test_case_catalog.yaml",
    "test_run_ledger": "quality/test_run_ledger.yaml",
    "test_data_contract": "quality/test_data_contract.yaml",
    "defect_register": "quality/defect_register.yaml",
    "environment_fingerprint": "quality/environment_fingerprint.yaml",
    "flake_policy": "quality/flake_policy.yaml",
}


def load_quality_artifacts(project_path: str | Path) -> tuple[dict[str, Any], list[str]]:
    project = Path(project_path)
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    for key, rel in QUALITY_FILES.items():
        path = project / "qa-context" / rel
        data = load_yaml(path)
        if data is None:
            missing.append(rel)
            loaded[key] = {}
        else:
            loaded[key] = data
    return loaded, missing


def validate_quality_packet(project_path: str | Path, policy: QualityPolicy | None = None) -> dict:
    project = Path(project_path)
    policy = policy or load_project_quality_policy(project)
    quality, missing_files = load_quality_artifacts(project)
    checks = {
        "process_catalog": validate_process_catalog(quality["process_catalog"], policy=policy),
        "traceability_matrix": validate_traceability_matrix(quality["traceability_matrix"]),
        "impact_analysis": validate_impact_analysis(quality["impact_analysis"]),
        "test_case_catalog": validate_test_case_catalog(quality["test_case_catalog"]),
        "test_run_ledger": validate_test_run_ledger(quality["test_run_ledger"], quality["test_case_catalog"]),
        "test_data_contract": validate_test_data_contract(quality["test_data_contract"]),
        "defect_register": validate_defect_register(quality["defect_register"]),
        "environment_fingerprint": validate_environment_fingerprint(quality["environment_fingerprint"]),
        "flake_policy": validate_flake_policy(quality["flake_policy"]),
    }
    fail_reasons = [f"missing_{rel}" for rel in missing_files]
    for name, check in checks.items():
        if not check["pass"]:
            fail_reasons.append(f"{name}_failed")
    return {
        "pass": not fail_reasons,
        "checks": checks,
        "missing_files": missing_files,
        "fail_reasons": sorted(set(fail_reasons)),
    }
