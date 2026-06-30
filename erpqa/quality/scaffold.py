from __future__ import annotations

from pathlib import Path
from typing import Any

from erpqa.core.paths import ensure_qa_context, write_yaml_if_missing


QUALITY_SCAFFOLD_FILES = [
    "quality/process_catalog.yaml",
    "quality/traceability_matrix.yaml",
    "quality/impact_analysis.yaml",
    "quality/test_case_catalog.yaml",
    "quality/test_run_ledger.yaml",
    "quality/test_data_contract.yaml",
    "quality/defect_register.yaml",
    "quality/environment_fingerprint.yaml",
    "quality/flake_policy.yaml",
    "quality_policy.yaml",
]


GENERIC_PROCESS_CATALOG: dict[str, Any] = {
    "processes": [{
        "process_id": "PROC-DEMO-001",
        "module": "DEMO",
        "owner": "qa-owner",
        "release_scope": "demo-release",
        "steps": [{
            "step_id": "enter-order",
            "sequence": 1,
            "screen_id": "DEMO-ORD-001M",
            "expected_state_change": "order_saved",
            "api": "POST /api/demo/orders",
            "tables": ["demo_order_header", "demo_order_line"],
        }],
    }]
}

GENERIC_TRACEABILITY_MATRIX: dict[str, Any] = {
    "links": [{
        "trace_id": "TR-DEMO-001",
        "requirement_id": "REQ-DEMO-001",
        "process_id": "PROC-DEMO-001",
        "screen_id": "DEMO-ORD-001M",
        "frontend": {
            "component": "frontend/routes/demo/orders/page.tsx",
            "view_config": "frontend/config/demo-order-view.yaml",
            "field_name": "order_qty",
        },
        "backend": {"dto": "backend/dto/DemoOrderDto.py", "service": "backend/services/demo_order.py"},
        "api": "POST /api/demo/orders",
        "sp": "usp_demo_order_list",
        "db_assertion": "db/assertions/demo_order.sql",
        "artifact_refs": [
            "frontend/routes/demo/orders/page.tsx",
            "frontend/config/demo-order-view.yaml",
            "backend/dto/DemoOrderDto.py",
            "backend/services/demo_order.py",
            "sql/procedures/usp_demo_order_list.sql",
        ],
        "test_case_id": "TC-DEMO-001",
        "finding_ids": ["F-DEMO-001"],
        "signoff_item": "SO-DEMO-001",
    }]
}

GENERIC_QUALITY_TEMPLATES: dict[str, dict[str, Any]] = {
    "quality/process_catalog.yaml": GENERIC_PROCESS_CATALOG,
    "quality/traceability_matrix.yaml": GENERIC_TRACEABILITY_MATRIX,
    "quality/impact_analysis.yaml": {
        "change_set": [{"path": "frontend/routes/demo/orders/page.tsx", "type": "route"}],
        "impact_rules": [{"change_type": "route", "maps_to": ["screen_route", "screen", "process", "test"]}],
        "affected_screens": ["DEMO-ORD-001M"],
        "affected_processes": ["PROC-DEMO-001"],
        "affected_tests": ["TC-DEMO-001"],
    },
    "quality/test_case_catalog.yaml": {
        "test_cases": [{
            "test_case_id": "TC-DEMO-001",
            "type": "manual",
            "process_id": "PROC-DEMO-001",
            "screen_id": "DEMO-ORD-001M",
            "risk": "high",
            "fixture_contract": "FX-DEMO-001",
            "expected_evidence": "manual/demo-001.md",
        }]
    },
    "quality/test_run_ledger.yaml": {
        "runs": [{
            "run_id": "RUN-DEMO-001",
            "test_case_id": "TC-DEMO-001",
            "runner": "qa-owner",
            "executed_at": "2026-06-30T00:00:00+00:00",
            "environment": "local-demo",
            "account": "qa-demo",
            "fixture": "UAT_DEMO_001",
            "evidence": "manual/demo-001.md",
            "result": "passed",
        }]
    },
    "quality/test_data_contract.yaml": {
        "fixtures": [{
            "fixture_id": "FX-DEMO-001",
            "prefix": "UAT_DEMO_",
            "cleanup_actions": ["DELETE FROM demo_order_line WHERE key LIKE 'UAT_DEMO_%'"],
            "residual_count": 0,
        }]
    },
    "quality/defect_register.yaml": {
        "defects": [{
            "defect_id": "DEF-DEMO-001",
            "severity": "minor",
            "state": "closed",
            "title": "Demo evidence placeholder closed",
        }]
    },
    "quality/environment_fingerprint.yaml": {
        "build_id": "local-demo-build",
        "frontend_commit": "local-copy",
        "backend_commit": "local-copy",
        "base_url": "https://erpqa-demo.invalid",
        "db_alias": "DEMO",
        "browser_device": "chromium-desktop",
        "account_role": "qa-demo",
    },
    "quality/flake_policy.yaml": {
        "retry_limit": 2,
        "flaky_when": "passes_after_retry",
        "quarantine": {"requires": ["owner", "reason", "expires_at"]},
        "score_penalty": {
            "flaky_impacted_test": 0.25,
            "quarantined_impacted_test": "fail_final_qa",
        },
    },
    "quality_policy.yaml": {
        "forbidden_source_roots": [],
        "impact_rules": [],
    },
}


def scaffold_quality_artifacts(project_path: str | Path) -> list[Path]:
    ensure_qa_context(project_path)
    written: list[Path] = []
    for relative_path in QUALITY_SCAFFOLD_FILES:
        written.append(write_yaml_if_missing(project_path, relative_path, GENERIC_QUALITY_TEMPLATES[relative_path]))
    return written
