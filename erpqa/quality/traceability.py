from __future__ import annotations

from erpqa.quality._common import list_items, require_fields, result


_LINK_FIELDS = [
    "trace_id",
    "requirement_id",
    "process_id",
    "screen_id",
    "frontend",
    "backend",
    "db_assertion",
    "test_case_id",
    "signoff_item",
]


def validate_traceability_matrix(matrix: dict) -> dict:
    missing: list[str] = []
    errors: list[str] = []
    links = list_items(matrix, "links")
    if not links:
        missing.append("links")
    for idx, link in enumerate(links):
        prefix = f"links[{idx}]"
        missing.extend(require_fields(link, _LINK_FIELDS, prefix))
        if not (link.get("api") or link.get("sp")):
            missing.append(f"{prefix}.api_or_sp")
        frontend = link.get("frontend")
        if isinstance(frontend, dict):
            missing.extend(require_fields(frontend, ["view_config", "field_name"], f"{prefix}.frontend"))
        else:
            errors.append(f"{prefix}.frontend must be a mapping")
    return result(missing, errors)


def finding_has_traceability(finding: dict, matrix: dict) -> bool:
    finding_id = finding.get("finding_id") or finding.get("id")
    if not finding_id:
        return False
    for link in list_items(matrix, "links"):
        if finding_id in link.get("finding_ids", []):
            return True
        if finding_id == link.get("defect_id"):
            return True
    return False


def _is_high_or_medium(finding: dict) -> bool:
    severity = str(finding.get("severity", "")).lower()
    confidence = str(finding.get("confidence", "")).lower()
    return severity in {"blocker", "major", "high", "medium"} or confidence == "high"


def traceability_coverage(findings: list[dict], matrix: dict) -> dict:
    scoped = [finding for finding in findings if _is_high_or_medium(finding)]
    eligible: list[str] = []
    unmapped: list[str] = []
    for finding in scoped:
        finding_id = finding.get("finding_id") or finding.get("id")
        if not finding_id:
            continue
        if finding_has_traceability(finding, matrix):
            eligible.append(finding_id)
        else:
            unmapped.append(finding_id)
    coverage = round(len(eligible) / len(scoped), 2) if scoped else 1.0
    return {
        "traceability_coverage": coverage,
        "eligible_findings": eligible,
        "unmapped_high_confidence_findings": unmapped,
        "pass": coverage >= 0.85 and not unmapped,
    }
