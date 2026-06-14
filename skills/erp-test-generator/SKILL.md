# ERP Test Generator Skill

## Purpose

Turn approved `DB_ASSERTION` rules into candidate SELECT-only SQL assertions for
deterministic safety checking and human review.

## Inputs

- `qa-context/rules/*.yaml`.
- `qa-context/entity_map.yaml`.
- `qa-context/flow_map.yaml`.

## Outputs

- Candidate SQL text in `DB_ASSERTION` rules.
- Generated SQL artifacts under `qa-context/generated/sql/` only after the
  deterministic CLI safety gate accepts them.

## Steps

1. Read each `DB_ASSERTION` rule.
2. Author SQL so returned rows indicate violations and zero rows means pass.
3. Use only a single SELECT statement.
4. Leave `sql: null` if schema or join semantics are unclear.
5. Let the deterministic CLI safety checker accept or reject the SQL.

## Guardrails

- Never connect to or execute against a database.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, EXECUTE, MERGE,
  CREATE, REPLACE, GRANT, REVOKE, or CALL in assertion SQL.
- Do not hide statements in comments, stacked queries, or encoded content.
- Do not generate third-party tool configs in the first release.

## Human-Approval Points

- Humans approve schema assumptions.
- Humans decide whether a rule is ready for downstream execution outside ERP QA Kit.

