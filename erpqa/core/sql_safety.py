"""Deterministic SELECT-only SQL safety checker.

Fail-safe policy notes:
- SQL comments (``--``, ``/* */``) are intentionally rejected inside the checked
  SQL string, since comments are a common way to hide trailing destructive
  statements. The generated ``.sql`` files add their own descriptive header
  comments to the *file*, not to the string that passes through this checker.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


DENY_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "EXECUTE",
    "EXEC",
    "MERGE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "CALL",
]


@dataclass(frozen=True)
class SqlSafetyResult:
    ok: bool
    reason: str
    normalized_sql: str = ""


def _semicolon_positions_outside_strings(sql: str) -> list[int]:
    positions: list[int] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            if in_single and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ";" and not in_single and not in_double:
            positions.append(i)
        i += 1
    return positions


def _replace_string_literals(sql: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            out.append(" ")
            if in_single and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_single = not in_single
        elif ch == '"' and not in_single:
            out.append(" ")
            in_double = not in_double
        elif in_single or in_double:
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def check_sql_safety(sql: str | None) -> SqlSafetyResult:
    if sql is None or not str(sql).strip():
        return SqlSafetyResult(False, "no SQL provided; needs schema confirmation")

    raw = str(sql).strip()
    if "--" in raw or "/*" in raw or "*/" in raw:
        return SqlSafetyResult(False, "comments are not allowed in assertion SQL")

    semicolons = _semicolon_positions_outside_strings(raw)
    if semicolons:
        last = semicolons[-1]
        if len(semicolons) > 1 or raw[last + 1 :].strip():
            return SqlSafetyResult(False, "multiple SQL statements are not allowed")
        raw = raw[:last].rstrip()

    comparable = _replace_string_literals(raw)
    if not re.match(r"^\s*SELECT\b", comparable, flags=re.IGNORECASE):
        return SqlSafetyResult(False, "SQL assertion must start with SELECT")

    # Tokenize into SQL identifier words and match denied keywords token-by-token.
    # Underscores and digits are identifier characters, so a column like
    # `created_at`/`updated_at`/`deleted_at` is a single token and never matches a
    # bare keyword such as CREATE/UPDATE/DELETE. This keeps the checker fail-safe
    # against standalone destructive operations without rejecting safe identifiers
    # that merely contain a denied keyword as a substring.
    tokens = set(re.findall(r"[A-Z_][A-Z0-9_]*", comparable.upper()))
    forbidden = sorted(tokens & set(DENY_KEYWORDS))
    if forbidden:
        return SqlSafetyResult(False, f"forbidden keyword detected: {forbidden[0]}")

    return SqlSafetyResult(True, "safe SELECT assertion", raw)

