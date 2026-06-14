# ERP QA Kit — Acceptance Criteria (Definition of Done)

This document is the **testable definition-of-done** for the first working release of
**ERP QA Kit**, read by an AI coding agent (Codex). Each item is a checkbox-style,
objectively verifiable criterion. Where a behavior is testable by a command, the exact
command and expected outcome are given. Given/When/Then is used where it clarifies intent.

This file does **not** restate the design. For the *why* and detailed behavior see
`SPEC.md`; for hard rules and prohibitions see `CONSTRAINTS.md`; for component layout and
data flow see `ARCHITECTURE.md`. Where those documents are authoritative, this file only
states the *observable acceptance check*.

**Conventions used below**
- "Provenance trio" = the three fields `source`, `confidence` (`high|medium|low`),
  `needs_human_confirmation` (`true|false`) that EVERY inferred item must carry.
- `<path>` / `<project_path>` = a target ERP project directory passed to each command.
- `DEMO` = `examples/pipe-manufacturing-demo/`.
- A criterion is **PASS** only when its check is literally reproducible by a human or CI.

---

## A. Repository & Structure

- [ ] **A1** The repository root contains the package dir `erpqa/` with at least:
  `erpqa/cli.py`, `erpqa/core/`, `erpqa/adapters/`, `erpqa/generators/`, `erpqa/reporters/`.
  *Check:* each path exists (`test -e`) and `core/`, `adapters/`, `generators/`,
  `reporters/` are directories containing at least one `*.py` module each.
- [ ] **A2** `docs/integrations.md` exists and is non-empty.
- [ ] **A3** `skills/` contains exactly these six skill specs, each as a `SKILL.md` file
  in its own subdir: `erp-intake/SKILL.md`, `erp-domain-modeler/SKILL.md`,
  `erp-rule-generator/SKILL.md`, `erp-test-generator/SKILL.md`,
  `erp-report-generator/SKILL.md`, `erp-fix-handoff/SKILL.md`.
  *Check:* all six files exist and are non-empty.
- [ ] **A4** `rule_packs/` exists and contains at least one rule pack file.
- [ ] **A5** `examples/pipe-manufacturing-demo/` exists and is a self-contained demo ERP project folder.
- [ ] **A6** `README.md` exists at repo root and is non-empty.
- [ ] **A7** The sibling docs `SPEC.md`, `CONSTRAINTS.md`, `ARCHITECTURE.md` exist at the
  paths referenced by this document.
- [ ] **A8** A test directory (`tests/`) exists with at least one test module per
  Section J requirement.
- [ ] **A9** The package is installable/runnable: an entry point named `erpqa` is exposed
  (e.g. via `pyproject.toml`/`setup.cfg` console_scripts) **or** `python -m erpqa`
  invokes the same CLI.

## B. CLI Surface

- [ ] **B1** All six subcommands exist on the `erpqa` CLI: `init`, `intake`, `validate`,
  `generate-sql`, `report`, `handoff`.
  *Check:* `erpqa --help` lists all six.
- [ ] **B2** Each subcommand accepts a single positional `<project_path>` argument.
  *Check:* `erpqa <cmd> --help` documents the positional path argument for each `<cmd>`.
- [ ] **B3** `erpqa --help` and `erpqa <cmd> --help` print usage text and exit `0`.
- [ ] **B4** Invoking a subcommand with a missing/invalid `<project_path>` prints a clear
  error and exits **non-zero** (not a traceback).
- [ ] **B5** Unknown subcommand or missing required argument prints usage and exits non-zero.
- [ ] **B6** Exit-code contract holds across the kit: `0` = success; non-zero = a
  validation/safety/usage failure (specific codes per `SPEC.md`).

## C. `init`

- [ ] **C1** Given an empty `<path>`, When `erpqa init <path>` runs, Then it scaffolds
  `<path>/qa-context/` containing: `project_manifest.yaml` (a stub), and the subdirs
  `rules/`, `generated/sql/`, `reports/`, `feedback/`, `handoff/`.
  *Check:* all listed paths exist after the command; exit `0`.
- [ ] **C2** Seed templates are written (e.g. seed `entity_map.yaml` / `flow_map.yaml` /
  rule template / feedback template per `SPEC.md`).
  *Check:* the documented seed/template files are present under `qa-context/`.
- [ ] **C3** `project_manifest.yaml` stub validates structurally enough that an immediate
  `erpqa validate <path>` does not crash (it may report "needs completion").
- [ ] **C4** **Idempotent:** running `erpqa init <path>` twice in a row exits `0` both
  times and does not error on the second run.
- [ ] **C5** **No unexpected clobber:** Given a user has edited a scaffolded file (e.g.
  added content to `project_manifest.yaml` or a rule), When `init` is re-run, Then
  existing user content is NOT silently overwritten (re-run either skips existing files
  or only creates missing ones; any overwrite requires an explicit `--force`-style flag).
  *Check:* edit a file, re-run `init`, confirm the edit survives.

## D. `intake`

- [ ] **D1** Given a populated ERP project at `<path>`, When `erpqa intake <path>` runs,
  Then it writes `qa-context/source_inventory.md`. *Check:* file exists; exit `0`.
- [ ] **D2** `source_inventory.md` classifies discovered sources into the six categories:
  **docs, DB schema, API specs, screen specs, backend, frontend**.
  *Check:* all six category labels appear as sections/headings in the output.
- [ ] **D3** `intake` fills/updates `qa-context/project_manifest.yaml` (the manifest
  changes from the `init` stub to reflect discovered sources).
- [ ] **D4** Each inferred inventory item records the **provenance trio**
  (`source`, `confidence`, `needs_human_confirmation`).
  *Check:* spot-check that inferred entries carry all three fields.
- [ ] **D5** `intake` is read-only with respect to the target ERP project: it does not
  modify any file outside `qa-context/`.
  *Check:* a file-mtime/diff snapshot of `<path>` excluding `qa-context/` is unchanged.

## E. YAML Schemas & `validate`

- [ ] **E1** `erpqa validate <path>` validates each of: `project_manifest.yaml`,
  `entity_map.yaml`, `flow_map.yaml`, every `rules/*.yaml`, and feedback YAML, against
  their required schemas.
- [ ] **E2** **entity_map** entries validate against the required field list:
  `entity, physical_table, module, type, primary_key, important_columns, status_columns,
  quantity_columns, amount_columns, source, confidence, needs_human_confirmation`.
- [ ] **E3** **flow_map** entries validate against: `flow_id, name, module, steps,
  trigger_screen, user_action, related_entities, affected_tables, status_transitions,
  downstream_side_effects, source, confidence, needs_human_confirmation`.
- [ ] **E4** **rule** entries validate against: `rule_id, name, module, flow, severity,
  verification_type, description, expected_result, required_entities, required_tables,
  sql, source, confidence, needs_human_confirmation`. `severity ∈ {BLOCKER, MAJOR, MINOR}`;
  `verification_type ∈ {DB_ASSERTION, API_ASSERTION, UI_ASSERTION, MANUAL}`.
- [ ] **E5** **feedback item** entries validate against: `feedback_id, title, module,
  related_flow, related_rule_id, severity, user_observed_behavior, expected_behavior,
  actual_behavior, reproduction_steps, evidence, affected_records, suspected_area,
  ai_fix_instruction, validation_after_fix, source, confidence, needs_human_confirmation`.
- [ ] **E6** **Provenance trio enforced:** validation fails for any inferred item missing
  `source`, `confidence`, or `needs_human_confirmation`, or with `confidence` not in
  `{high, medium, low}` or `needs_human_confirmation` not boolean.
- [ ] **E7** **Actionable error reporting:** Given a YAML with a missing/invalid required
  field, When `validate` runs, Then the reported error names BOTH the **file** and the
  **field** at fault. *Check:* delete one required field, run `validate`, confirm file+field appear in the message.
- [ ] **E8** **Non-zero exit on schema failure:** any schema failure makes
  `erpqa validate <path>` exit non-zero; a fully valid project exits `0`.
- [ ] **E9** A clean, fully-populated demo (`DEMO`) passes `erpqa validate DEMO` with exit `0`.

## F. `generate-sql` & SQL Safety

- [ ] **F1** Given approved `DB_ASSERTION` rules at `<path>`, When `erpqa generate-sql <path>`
  runs, Then for each such rule it runs the SQL safety checker and writes a SELECT-only
  `.sql` assertion file into `qa-context/generated/sql/`. *Check:* `.sql` files appear; exit `0`.
- [ ] **F2** **Forbidden keywords rejected (each individually):** the safety checker
  rejects SQL containing any of `INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC,
  EXECUTE, MERGE, CREATE, REPLACE, GRANT, REVOKE, CALL`. *Check:* one negative test per
  keyword; each is rejected **with a reason** and no `.sql` file is emitted for it.
- [ ] **F3** **Multi-statement rejected:** SQL with multiple statements (e.g.
  `SELECT ...; DROP TABLE x;`) is rejected with a reason.
- [ ] **F4** **Hidden/suspicious destructive statement rejected:** destructive SQL hidden
  via comments, encoding, or trailing statements (e.g. `SELECT 1 -- \n; DELETE FROM t`) is
  rejected with a reason.
- [ ] **F5** **Valid SELECT accepted:** a well-formed read-only `SELECT` assertion passes
  the checker and a corresponding `.sql` file is written.
- [ ] **F6** **"Rows only when violations exist" documented:** every generated `.sql` file
  contains an explicit comment/header stating it returns rows ONLY when violations exist
  (empty result = pass). *Check:* grep the generated files for that statement.
- [ ] **F7** **No-safe-SQL → NEEDS_SCHEMA_CONFIRMATION:** Given a `DB_ASSERTION` rule for
  which no safe SQL can be produced, Then the rule is marked
  `NEEDS_SCHEMA_CONFIRMATION` (not silently dropped) and no `.sql` is emitted for it.
- [ ] **F8** **No DB execution ever:** `generate-sql` never opens a database connection and
  never executes SQL against any DB. *Check:* no DB driver connection is invoked
  (verified by test double / no network or DB I/O); per `CONSTRAINTS.md`.
- [ ] **F9** Rejections are surfaced clearly (reasons listed in output and/or a generated
  report artifact), and the command's exit code reflects the documented contract in `SPEC.md`.

## G. `report`

- [ ] **G1** `erpqa report <path>` generates at least one Markdown report into
  `qa-context/reports/`. *Check:* a `*.md` report exists; exit `0`.
- [ ] **G2** The report includes an **entities** summary (from `entity_map`).
- [ ] **G3** The report includes a **flows** summary (from `flow_map`).
- [ ] **G4** The report includes a **rules** summary.
- [ ] **G5** The report includes a **severity breakdown** (BLOCKER/MAJOR/MINOR counts).
- [ ] **G6** The report includes a **confidence breakdown** (high/medium/low).
- [ ] **G7** The report includes a dedicated **"Needs Human Confirmation"** section listing
  every item with `needs_human_confirmation: true` (and/or low confidence).
  *Check:* an item flagged in source YAML appears in that section.

## H. `handoff`

- [ ] **H1** `erpqa handoff <path>` reads all required inputs: `qa-context/reports/`,
  `rules/`, `entity_map.yaml`, `flow_map.yaml`, and `feedback/`. *Check:* exit `0` on a valid project.
- [ ] **H2** It generates `qa-context/handoff/fix_handoff.md`.
- [ ] **H3** It generates `qa-context/handoff/codex_fix_prompt.md`.
- [ ] **H4** If missing, it creates `qa-context/feedback/feedback_items.yaml`.
- [ ] **H5** If missing, it creates `qa-context/feedback/PM_FEEDBACK_TEMPLATE.md`.
- [ ] **H6** **Six capabilities covered:** the handoff content demonstrably enables an AI
  coding agent to: (1) locate the likely affected module/code path; (2) understand
  expected vs actual behavior; (3) inspect related rules and SQL assertions; (4) implement
  a fix in the target ERP codebase; (5) add/update tests; (6) rerun validation after the
  fix. *Check:* each of the six is addressed by an explicit section/instruction in
  `fix_handoff.md` and/or `codex_fix_prompt.md`.
- [ ] **H7** **No target-code modification:** `handoff` (and the whole toolkit) never
  auto-modifies the target ERP codebase; it only writes under `qa-context/`.
  *Check:* diff of `<path>` excluding `qa-context/` is empty after running; per `CONSTRAINTS.md`.
- [ ] **H8** Re-running `handoff` does not clobber a user-edited `feedback_items.yaml` or
  `PM_FEEDBACK_TEMPLATE.md` (creates only if missing).

## I. Demo End-to-End

- [ ] **I1** Running the full pipeline in order on the demo succeeds end-to-end:
  ```
  erpqa init examples/pipe-manufacturing-demo
  erpqa intake examples/pipe-manufacturing-demo
  erpqa validate examples/pipe-manufacturing-demo
  erpqa generate-sql examples/pipe-manufacturing-demo
  erpqa report examples/pipe-manufacturing-demo
  erpqa handoff examples/pipe-manufacturing-demo
  ```
  *Check:* every command exits `0` in sequence.
- [ ] **I2** After the run, all expected artifacts exist under
  `examples/pipe-manufacturing-demo/qa-context/`: updated `project_manifest.yaml`,
  `source_inventory.md`, `entity_map.yaml`, `flow_map.yaml`, `rules/*.yaml`,
  `generated/sql/*.sql`, `reports/*.md`, `handoff/fix_handoff.md`,
  `handoff/codex_fix_prompt.md`, `feedback/feedback_items.yaml`,
  `feedback/PM_FEEDBACK_TEMPLATE.md`.
- [ ] **I3** The demo ships **inventory** rules using generic placeholder tables covering:
  receipt→movement, stock not negative, shipment decreases stock, cancellation restores stock.
- [ ] **I4** The demo ships **purchase** rules covering: receipt updates PO received qty,
  cancelled PO blocks receipt.
- [ ] **I5** The demo ships **production** rules covering: completion→movement,
  good+defect = total output, output ≤ work-order qty (unless explicitly allowed).
- [ ] **I6** All demo rules use **generic placeholder table names only** (no real/customer
  schema names); per `CONSTRAINTS.md`.
- [ ] **I7** At least one demo `DB_ASSERTION` rule yields a written SELECT-only `.sql`
  assertion, and (if applicable) at least one demonstrates the
  `NEEDS_SCHEMA_CONFIRMATION` path.

## J. Tests

- [ ] **J1** A basic automated test suite exists and **passes**: `pytest` (or the documented
  runner) exits `0`.
- [ ] **J2** **SQL safety tests:** one rejection test per forbidden keyword
  (`INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, EXECUTE, MERGE, CREATE, REPLACE,
  GRANT, REVOKE, CALL`), plus a multi-statement rejection test and a hidden-statement
  rejection test, plus a valid-SELECT acceptance test.
- [ ] **J3** **YAML schema validation tests:** a passing-case test per schema type
  (`project_manifest`, `entity_map`, `flow_map`, `rule`, `feedback`) AND at least one
  **missing-field failure** test that asserts a non-zero/validation error naming the
  offending field.
- [ ] **J4** **End-to-end smoke test:** a test runs the full six-command pipeline on the
  demo and asserts every expected artifact (per I2) is produced.
- [ ] **J5** Tests assert that no DB connection is opened during `generate-sql` (e.g. via a
  guard/mock that fails if a connection is attempted).
- [ ] **J6** Tests assert the toolkit never writes outside `qa-context/` for the target project.

## K. Documentation

- [ ] **K1** `README.md` documents installation AND the full pipeline usage (the ordered
  six-command flow with `<project_path>`), runnable as-written against the demo.
- [ ] **K2** `docs/integrations.md` is present and describes how the kit integrates with an
  AI coding agent (e.g. Codex) and the target ERP codebase.
- [ ] **K3** All six skill specs under `skills/*/SKILL.md` are present and each describes
  its skill's purpose, inputs, and outputs.
- [ ] **K4** README cross-references `SPEC.md`, `CONSTRAINTS.md`, and `ARCHITECTURE.md`
  rather than duplicating their content.

## L. Definition of Done (consolidated)

The first working release is **DONE** only when ALL of the following hold:

- [ ] **L1** Sections **A–K** are fully checked.
- [ ] **L2** The six-command pipeline runs **end-to-end on the demo** with every command
  exiting `0` and producing every expected artifact (I1–I2).
- [ ] **L3** `erpqa validate examples/pipe-manufacturing-demo` exits `0` on the clean demo,
  and exits non-zero when a required field is removed (E7–E9).
- [ ] **L4** The SQL safety checker rejects every forbidden keyword, multi-statement, and
  hidden-statement case, and accepts valid SELECT-only assertions (F2–F5), with no DB
  connection ever opened (F8/J5).
- [ ] **L5** The handoff artifacts cover all six AI-coding-agent capabilities (H6) and the
  toolkit never modifies target ERP code (H7/J6).
- [ ] **L6** `pytest` passes, including the SQL-safety, schema-validation (with a
  missing-field failure), and end-to-end smoke tests (J1–J4).
- [ ] **L7** README + `docs/integrations.md` + six `SKILL.md` specs are present and
  accurate (Section K).
