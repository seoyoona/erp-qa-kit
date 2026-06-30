from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


def validate_test_data_contract(contract: dict) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    fixtures = list_items(contract, "fixtures")
    if not fixtures:
        missing.append("fixtures")
    for idx, fixture in enumerate(fixtures):
        prefix = f"fixtures[{idx}]"
        missing.extend(require_fields(fixture, ["fixture_id", "prefix", "cleanup_actions"], prefix))
        if "residual_count" not in fixture:
            missing.append(f"{prefix}.residual_count")
        elif fixture.get("residual_count") != 0:
            errors.append(f"{prefix}.residual_count must be 0")
    return result(missing, errors)
