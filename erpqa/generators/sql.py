from __future__ import annotations

from pathlib import Path

from erpqa.core.constants import NEEDS_SCHEMA_CONFIRMATION
from erpqa.core.paths import ensure_qa_context, qa_output_path, write_text, write_yaml
from erpqa.core.sql_safety import check_sql_safety
from erpqa.core.yaml_io import load_yaml


HEADER = (
    "-- ERP QA Kit assertion: returns rows ONLY when violations exist "
    "(empty result = pass).\n"
    "-- Generated for review; ERP QA Kit does not execute this SQL.\n\n"
)


def _rule_files(project_path: str | Path) -> list[Path]:
    return sorted((Path(project_path).resolve() / "qa-context" / "rules").glob("*.yaml"))


def load_rules(project_path: str | Path) -> list[dict[str, object]]:
    rules: list[dict[str, object]] = []
    for file in _rule_files(project_path):
        data = load_yaml(file) or {}
        for rule in data.get("rules", []):
            if isinstance(rule, dict):
                item = dict(rule)
                item["_file"] = str(file)
                rules.append(item)
    return rules


def generate_sql(project_path: str | Path) -> list[dict[str, str]]:
    ensure_qa_context(project_path)
    sql_dir = qa_output_path(project_path, "generated/sql")
    sql_dir.mkdir(parents=True, exist_ok=True)
    for old_sql in sorted(sql_dir.glob("*.sql")):
        old_sql.unlink()

    statuses: list[dict[str, str]] = []
    for rule in load_rules(project_path):
        rule_id = str(rule.get("rule_id", "unknown_rule"))
        verification_type = str(rule.get("verification_type", ""))
        if verification_type != "DB_ASSERTION":
            statuses.append({"rule_id": rule_id, "status": "N/A", "reason": "non-DB_ASSERTION rule"})
            continue

        sql = rule.get("sql")
        if sql is None or not str(sql).strip():
            statuses.append(
                {
                    "rule_id": rule_id,
                    "status": NEEDS_SCHEMA_CONFIRMATION,
                    "reason": "rule has no safe SQL; human schema confirmation required",
                }
            )
            continue

        result = check_sql_safety(str(sql))
        if not result.ok:
            statuses.append({"rule_id": rule_id, "status": "UNSAFE", "reason": result.reason})
            continue

        write_text(project_path, f"generated/sql/{rule_id}.sql", HEADER + result.normalized_sql + "\n")
        statuses.append({"rule_id": rule_id, "status": "OK", "reason": "safe SELECT assertion emitted"})

    write_yaml(project_path, "generated/sql/generation_status.yaml", {"sql_generation": statuses})
    return statuses

