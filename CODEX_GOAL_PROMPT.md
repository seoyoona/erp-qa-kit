# Codex /Goal Prompt (paste into Codex)

> Copy everything in the code block below into Codex `/Goal`.

```
Read INDEX.md first, then follow its reading order (SPEC.md → CONSTRAINTS.md →
ARCHITECTURE.md → ROADMAP.md Phase 1 → ACCEPTANCE_CRITERIA.md → docs/integrations.md →
README_DRAFT.md). These repository documents are the single source of truth.

Goal: implement the FIRST WORKING LOCAL RELEASE of ERP QA Kit so the full pipeline runs
end-to-end on examples/pipe-manufacturing-demo/:
init → intake → validate → generate-sql → report → handoff.

Rules:
- Build exactly what the binding documents specify. Do NOT invent requirements, features,
  dependencies, links, or table names beyond them.
- Treat CONSTRAINTS.md as hard limits (local/offline, SELECT-only SQL with NO database
  execution, never modify target ERP code, human-approval gates, provenance on every
  inferred item). Constraints override convenience.
- Treat ACCEPTANCE_CRITERIA.md as the definition of done; build toward it and self-verify
  every criterion (sections A–L) before declaring completion.
- docs/integrations.md lists FUTURE integration targets only — design the rule IR's
  exporter extension points, but implement NONE of those tools. Do not search the web; use
  its links verbatim if referenced.
- ROADMAP.md Phases 2–6 are future scope — do not implement them.

Deliver: the local Python `erpqa` CLI (init, intake, validate, generate-sql, report,
handoff), the qa-context structure and YAML schemas + validation, the SELECT-only SQL
safety checker and DB_ASSERTION→SQL generation, Markdown report generation, the
feedback-to-fix handoff generation, the pipe-manufacturing demo, the six skills/*/SKILL.md
specs, basic tests, and a finalized README.md (from README_DRAFT.md). Suggested build order
is in ROADMAP.md §3. When done, confirm the demo runs end-to-end and list which
ACCEPTANCE_CRITERIA sections pass.
```
