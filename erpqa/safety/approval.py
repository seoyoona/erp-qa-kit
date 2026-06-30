from __future__ import annotations


def normalize_approval(data: dict) -> dict:
    return {
        "approved_by": str(data.get("approved_by", "")).strip(),
        "scope": str(data.get("scope", "")).strip(),
        "allowed_methods": [str(method).upper() for method in data.get("allowed_methods", [])],
        "forbidden_methods": [str(method).upper() for method in data.get("forbidden_methods", [])],
        "fixture_prefix": data.get("fixture_prefix") or "",
        "cleanup_required": bool(data.get("cleanup_required", False)),
        "residual_count_required": bool(data.get("residual_count_required", False)),
        "expires_at": data.get("expires_at") or "",
    }


def approval_allows(approval: dict, method: str, fixture_key: str = "") -> bool:
    method = method.upper()
    if method in approval.get("forbidden_methods", []):
        return False
    if method not in approval.get("allowed_methods", []):
        return False
    prefix = approval.get("fixture_prefix") or ""
    if method != "GET" and prefix and not fixture_key.startswith(prefix):
        return False
    return bool(approval.get("approved_by") and approval.get("scope"))
