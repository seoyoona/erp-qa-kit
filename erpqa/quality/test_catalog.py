from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


_REQUIRED_TYPES = {"manual", "browser", "api", "db_readonly", "write_uat"}
_CASE_FIELDS = [
    "test_case_id",
    "type",
    "process_id",
    "screen_id",
    "risk",
    "fixture_contract",
    "expected_evidence",
]


def validate_test_case_catalog(catalog: dict) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    cases = list_items(catalog, "test_cases")
    if not cases:
        missing.append("test_cases")
    seen_types = set()
    for idx, case in enumerate(cases):
        prefix = f"test_cases[{idx}]"
        missing.extend(require_fields(case, _CASE_FIELDS, prefix))
        case_type = case.get("type")
        if case_type:
            seen_types.add(case_type)
        if case_type and case_type not in _REQUIRED_TYPES:
            errors.append(f"{prefix}.type unsupported: {case_type}")
    for missing_type in sorted(_REQUIRED_TYPES - seen_types):
        missing.append(f"test_cases.type:{missing_type}")
    return result(missing, errors)
