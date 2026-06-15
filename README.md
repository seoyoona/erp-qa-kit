# ERP QA Kit

ERP QA Kit is a local, file-based Python CLI for ERP data-integrity QA. It reads
a target ERP project folder, builds a `qa-context/` workspace, validates
human-reviewable YAML artifacts, generates SELECT-only SQL assertions from
`DB_ASSERTION` rules, renders Markdown reports, and produces fix-handoff
documents for a separate coding agent. v0.2 adds policy-backed, module-scoped
screen-contract audits over extracted source folders.

The core rule is: **LLMs propose, deterministic checks verify, humans approve.**
ERP QA Kit never modifies target ERP application code and never connects to or
executes SQL against a database.

For the full contract, see `SPEC.md`, `CONSTRAINTS.md`, and `ARCHITECTURE.md`.
The release checklist is in `ACCEPTANCE_CRITERIA.md`.

## Installation

Requirements:

- Python 3.11+
- PyYAML
- openpyxl
- No database, network service, API key, or browser automation engine

Install from a local checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

You can also run the CLI without installing the console script:

```bash
python -m erpqa --help
```

## Demo Quickstart

The bundled demo is `examples/pipe-manufacturing-demo/`. Run the six-command
pipeline in order:

```bash
export DEMO=examples/pipe-manufacturing-demo

erpqa init $DEMO
erpqa intake $DEMO
erpqa validate $DEMO
erpqa generate-sql $DEMO
erpqa report $DEMO
erpqa handoff $DEMO
```

Equivalent module form:

```bash
python -m erpqa init examples/pipe-manufacturing-demo
python -m erpqa intake examples/pipe-manufacturing-demo
python -m erpqa validate examples/pipe-manufacturing-demo
python -m erpqa generate-sql examples/pipe-manufacturing-demo
python -m erpqa report examples/pipe-manufacturing-demo
python -m erpqa handoff examples/pipe-manufacturing-demo
```

All generated artifacts live under:

```text
examples/pipe-manufacturing-demo/qa-context/
```

Nothing outside `qa-context/` is written by the toolkit.

## Module Audit Quickstart

The bundled v0.2 fixture is `examples/module-audit-fixture/`. It contains a
module-scoped extracted folder for module `ORD`:

```bash
python -m erpqa policy-init examples/module-audit-fixture
# Review qa-context/project_policy.yaml, then set draft: false and human_confirmed: true.
python -m erpqa module-init examples/module-audit-fixture --module ORD
python -m erpqa module-audit examples/module-audit-fixture --module ORD
python -m erpqa validate examples/module-audit-fixture
```

`module-audit` runs the granular v0.2 commands in order:

```text
extract-spec
extract-frontend
extract-backend
extract-procedure
compare-contract
module-report
module-handoff
```

Each module command reads `project_policy.yaml`, `project_memory.md`,
`module_policy.yaml`, and `module_memory.md` before doing stage work. Draft
project policies halt module commands until a human confirms the policy.

## CLI Commands

Each subcommand takes one required positional `<project_path>`:

- `erpqa init <project_path>` creates the `qa-context/` scaffold and templates.
- `erpqa intake <project_path>` scans local files, writes `source_inventory.md`,
  and refreshes `project_manifest.yaml`.
- `erpqa validate <project_path>` validates manifest, entity map, flow map,
  rules, feedback, provenance, references, and SQL safety.
- `erpqa generate-sql <project_path>` writes safe SELECT-only SQL assertions for
  `DB_ASSERTION` rules and records generation status.
- `erpqa report <project_path>` writes `reports/qa_report.md`.
- `erpqa handoff <project_path>` writes `handoff/fix_handoff.md` and
  `handoff/codex_fix_prompt.md`, creating feedback templates only if missing.
- `erpqa policy-init <project_path>` creates project policy, memory, and
  assumption seed files without clobbering existing human edits.
- `erpqa module-init <project_path> --module <MODULE>` scaffolds a module
  workspace under `qa-context/modules/<MODULE>/`.
- `erpqa extract-spec <project_path> --module <MODULE>` writes
  `screen_contract.yaml` from extracted spec files.
- `erpqa extract-frontend <project_path> --module <MODULE>` writes
  `frontend_contract.yaml` from static frontend source evidence.
- `erpqa extract-backend <project_path> --module <MODULE>` writes
  `backend_contract.yaml` from static backend source evidence.
- `erpqa extract-procedure <project_path> --module <MODULE>` writes
  `procedure_contract.yaml` from static SQL text only.
- `erpqa compare-contract <project_path> --module <MODULE>` writes
  `comparison_findings.yaml`.
- `erpqa module-report <project_path> --module <MODULE>` writes module mismatch,
  column, frontend-contract, and procedure-mapping reports.
- `erpqa module-handoff <project_path> --module <MODULE>` writes frontend-fix
  handoff documents.
- `erpqa module-audit <project_path> --module <MODULE>` orchestrates the v0.2
  module workflow end to end.

Exit code `0` means the command completed. Non-zero exits indicate usage or
validation failures; `generate-sql` reports unsafe rules and continues by
default without emitting unsafe `.sql` files.

## `qa-context/` Layout

```text
qa-context/
  project_manifest.yaml
  project_policy.yaml
  project_memory.md
  project_assumptions.yaml
  source_inventory.md
  entity_map.yaml
  flow_map.yaml
  rules/
  generated/
    sql/
  reports/
  feedback/
    feedback_items.yaml
    PM_FEEDBACK_TEMPLATE.md
  handoff/
    fix_handoff.md
    codex_fix_prompt.md
  modules/
    ORD/
      module_manifest.yaml
      module_policy.yaml
      module_memory.md
      screen_contract.yaml
      frontend_contract.yaml
      backend_contract.yaml
      procedure_contract.yaml
      comparison_findings.yaml
      reports/
      handoff/
```

`init` preserves existing files. Derived artifacts such as source inventory,
generated SQL, reports, and handoff docs are overwritten when their commands are
rerun. Human-authored maps, rules, and feedback files are not silently clobbered.

## Provenance and Human Review

Every inferred entity, flow, rule, feedback item, and inventory classification
must carry:

- `source`
- `confidence` as `high`, `medium`, or `low`
- `needs_human_confirmation` as `true` or `false`

Low and medium confidence items must require human confirmation. Humans approve
business meaning, rule severity, release decisions, and final fixes.

## SQL Safety

`generate-sql` only emits SQL that passes the deterministic safety checker:

- one statement only;
- starts with `SELECT`;
- rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`,
  `EXECUTE`, `MERGE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, and `CALL`;
- rejects comments and stacked statements;
- writes a header stating that rows are returned only when violations exist.

If a `DB_ASSERTION` rule has no safe SQL, its generated status is
`NEEDS_SCHEMA_CONFIRMATION`; no `.sql` file is emitted for that rule.

ERP QA Kit does not execute generated SQL and does not import database drivers.

## v0.2 Extractors

Required extractors are real, deterministic adapters wired to the module CLI:

- `xlsx_text_adapter` and `xlsx_image_manifest_adapter` use openpyxl. The image
  adapter lists embedded images and positions only; it performs no OCR.
- `csv_adapter`, `markdown_adapter`, `json_yaml_adapter`,
  `frontend_static_adapter`, `backend_static_adapter`, and
  `procedure_sql_adapter` use the Python standard library plus PyYAML where
  applicable.

`pandas` and `markitdown` are optional extras only and are imported lazily. Their
absence does not break the required v0.2 flow. Docling and Unstructured are
future-only: they are documented in the v0.2 planning docs but not implemented,
not imported, and not declared as dependencies.

## Handoff Workflow

A PM or QA lead records structured feedback in
`qa-context/feedback/feedback_items.yaml` or drafts notes in
`PM_FEEDBACK_TEMPLATE.md`. Then:

```bash
erpqa handoff <project_path>
```

The handoff artifacts tell a downstream coding agent how to locate the likely
module or code path, understand expected versus actual behavior, inspect related
rules and SQL assertions, implement a fix in the target ERP codebase, add or
update tests, and rerun validation.

The actual code change happens outside ERP QA Kit, in the target ERP repository,
under human approval.

## Future Integrations

`docs/integrations.md` documents future targets such as Great Expectations, Soda
Core, dbt, Schemathesis, Keploy, Playwright, GraphWalker, and AltWalker. None of
those tools are installed, imported, executed, or implemented in this release.

## Tests

The automated test suite uses the Python standard library runner:

```bash
python -m unittest discover -s tests
```

The repository also includes a small local test-runner shim, `run_tests.py`,
which delegates to unittest and does not add pytest as a dependency:

```bash
python3 run_tests.py -q
```

It is named `run_tests.py` (not `pytest.py`) so it never shadows the real
`pytest` module.
