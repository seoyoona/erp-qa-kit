from __future__ import annotations

from erpqa.quality._common import require_fields, result


_FINGERPRINT_FIELDS = [
    "build_id",
    "frontend_commit",
    "backend_commit",
    "base_url",
    "db_alias",
    "browser_device",
    "account_role",
]


def validate_environment_fingerprint(fingerprint: dict) -> dict:
    return result(require_fields(fingerprint, _FINGERPRINT_FIELDS, "environment_fingerprint"), [])
