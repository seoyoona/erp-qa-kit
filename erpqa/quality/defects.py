from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


ALLOWED_STATES = {"candidate", "confirmed", "fixed", "retested", "closed", "rejected"}


def validate_defect_register(defect_register: dict) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    defects = list_items(defect_register, "defects")
    if "defects" not in defect_register:
        missing.append("defects")
    for idx, defect in enumerate(defects):
        prefix = f"defects[{idx}]"
        missing.extend(require_fields(defect, ["defect_id", "severity", "state", "title"], prefix))
        state = defect.get("state")
        if state and state not in ALLOWED_STATES:
            errors.append(f"{prefix}.state unsupported: {state}")
        if state == "rejected":
            missing.extend(require_fields(defect, ["rejection_reason", "rejected_by"], prefix))
    return result(missing, errors)


def defect_gate_passed(defect_register: dict, test_run_ledger: dict) -> dict:
    open_blocker_major: list[str] = []
    needs_retest: list[str] = []
    rejected_without_reason: list[str] = []
    retested_defects = {
        run.get("defect_link")
        for run in list_items(test_run_ledger, "runs")
        if run.get("defect_link") and run.get("result") in {"passed", "failed"}
    }
    for defect in list_items(defect_register, "defects"):
        defect_id = defect.get("defect_id")
        severity = str(defect.get("severity", "")).lower()
        state = defect.get("state")
        if state == "confirmed" and severity in {"blocker", "major", "high"}:
            open_blocker_major.append(defect_id)
        if state == "fixed" and defect_id not in retested_defects:
            needs_retest.append(defect_id)
        if state == "rejected" and not (defect.get("rejection_reason") and defect.get("rejected_by")):
            rejected_without_reason.append(defect_id)
    passed = not (open_blocker_major or needs_retest or rejected_without_reason)
    return {
        "open_blocker_major": open_blocker_major,
        "needs_retest": needs_retest,
        "rejected_without_reason": rejected_without_reason,
        "pass": passed,
    }
