from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


def validate_flake_policy(policy: dict) -> dict:
    missing = require_fields(policy, ["retry_limit", "flaky_when", "quarantine", "score_penalty"], "flake_policy")
    quarantine = policy.get("quarantine")
    if isinstance(quarantine, dict) and not quarantine.get("requires"):
        missing.append("flake_policy.quarantine.requires")
    penalty = policy.get("score_penalty")
    if isinstance(penalty, dict):
        missing.extend(require_fields(penalty, ["flaky_impacted_test", "quarantined_impacted_test"], "flake_policy.score_penalty"))
    return result(missing, [])


def apply_flake_policy(test_run_ledger: dict, policy: dict) -> dict:
    retry_limit = int(policy.get("retry_limit", 0) or 0)
    flaky: list[str] = []
    quarantined: list[str] = []
    errors: list[str] = []
    for idx, run in enumerate(list_items(test_run_ledger, "runs")):
        attempts = int(run.get("attempts", 1) or 1)
        test_id = run.get("test_case_id")
        if attempts > 1 and run.get("result") == "passed":
            flaky.append(test_id)
        if attempts > retry_limit + 1:
            errors.append(f"runs[{idx}].attempts exceeds retry_limit")
        if run.get("quarantined"):
            quarantined.append(test_id)
            for field in policy.get("quarantine", {}).get("requires", []):
                if not run.get(field):
                    errors.append(f"runs[{idx}].{field} required for quarantine")
    return {
        "flaky_tests": flaky,
        "quarantined_tests": quarantined,
        "errors": errors,
        "pass": not errors and not quarantined,
    }
