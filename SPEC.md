# ERP QA Kit — SPEC.md

> **Status:** Source of truth for the first working release.
> **Audience:** AI coding agent (Codex) invoked via `/Goal`, plus human maintainers.
> **Sibling docs:** `CONSTRAINTS.md` (hard rules), `ACCEPTANCE_CRITERIA.md` (test gates), `ARCHITECTURE.md` (module decomposition), `ROADMAP.md` (sequencing), `docs/integrations.md` (future export targets). This SPEC references those by name and does not duplicate their full content.

---

## 1. Overview & Product Positioning

**ERP QA Kit** is an open-source, **local-file-based, AI-assisted ERP data-integrity QA framework**. It reads an ERP project folder; classifies its docs / DB schema / API specs / screen specs / backend / frontend files; builds a QA context; models ERP entities and business flows; generates human-reviewable data-integrity rules; converts approved `DB_ASSERTION` rules into SELECT-only SQL assertions; generates Markdown QA reports; and turns QA findings + PM feedback into AI-readable **fix-handoff** documents for a coding agent (Codex/Claude).

### What it IS
- A local **Python CLI** (`erpqa`) operating on files in a project folder.
- An **assistant** that proposes structure, then verifies deterministically, then defers to humans for meaning.
- A producer of **human-reviewable artifacts** (YAML, Markdown, `.sql`) under `qa-context/`.
- A producer of **AI-readable fix-handoff documents** so a coding agent can investigate and fix issues in the *target* ERP codebase.

### What it is NOT
- **NOT** a browser QA bot.
- **NOT** a dashboard or web app.
- **NOT** a one-off script.
- **NOT** a tool that connects to or executes SQL against a real/production database (first release).
- **NOT** a tool that ever modifies target ERP application code.

### Core Principle (3-layer responsibility)
| Layer | Responsibility | Examples |
|-------|----------------|----------|
| **LLM PROPOSES** | Structure, mappings, flows, rules, fix-handoff drafts | entity_map, flow_map, candidate rules, draft handoff |
| **DETERMINISTIC VERIFIES** | SQL safety, YAML schema validation, report/file generation | SELECT-only checker, schema validator, Markdown renderer |
| **HUMAN APPROVES** | Business meaning, severity, release decisions, final fixes | rule approval, severity, "ship/no-ship", code merges |

### Target User
A **non-developer PM or QA lead** must be able to run the pipeline and read/act on outputs. The toolkit must not stop at *detecting* issues — it must produce documents a coding agent can act on. It must **never** auto-modify target ERP code.

---

## 2. Goals & Non-Goals (First Release)

### Goals (in scope)
- Local Python CLI named `erpqa`.
- `qa-context/` initialization/scaffolding.
- Project-folder **intake** and **source inventory**; `source_inventory.md` generation.
- YAML formats + **schema validation**.
- `project_manifest.yaml`, `entity_map.yaml`, `flow_map.yaml`, rule YAML files.
- **SELECT-only SQL safety checker**.
- `DB_ASSERTION` rule YAML → `.sql` assertion generation.
- Markdown **report** generation.
- Feedback-to-fix **handoff** generation.
- Bundled **pipe-manufacturing demo** project.
- Basic **tests**.
- **README** usage guide.
- Six **SKILL.md** spec files.
- `docs/integrations.md`.

### Non-Goals (explicitly NOT now)
Dashboard; Playwright implementation; API test generation; real DB connection or SQL execution against a DB; production DB access; auto page crawler; SaaS / multi-tenant; GraphWalker / model-based-testing implementation; GitHub marketplace/action; complex plugin system; direct integration with heavy third-party QA engines; automatic modification of target ERP application code.

See `ROADMAP.md` for when out-of-scope items may be sequenced. See `CONSTRAINTS.md` for the hard guardrails behind these non-goals.

---

## 3. Pilot Context

The pilot target is a **pipe-manufacturing ERP**:
- **~7 modules**, **~140 pages**.
- CRUD-heavy with **cross-module data consistency** as the critical risk area.
- Representative concerns: inventory movements, purchase receipts, production results, shipment stock effects.

A trimmed, **generic-placeholder** version of this domain ships as `examples/pipe-manufacturing-demo/` and the full pipeline MUST run end-to-end on it. **Never** use real company names; use generic table names only (see §13).

---

## 4. End-to-End Pipeline

Order: `init → intake → validate → generate-sql → report → handoff`. Each command operates on a `<project_path>` and reads/writes under `<project_path>/qa-context/`.

| # | Command | Consumes | Produces |
|---|---------|----------|----------|
| 1 | `erpqa init <project_path>` | project folder (path) | `qa-context/` scaffold: directories + stub `project_manifest.yaml`, empty `entity_map.yaml`/`flow_map.yaml`, `rules/`, `generated/sql/`, `reports/`, `feedback/`, `handoff/` |
| 2 | `erpqa intake <project_path>` | project files (docs, schema, API/screen specs, backend, frontend) | `source_inventory.md`, populated `project_manifest.yaml` (classified inventory + module list) |
| 3 | `erpqa validate <project_path>` | all `qa-context/*.yaml` and `rules/*.yaml` | validation report (stdout + non-zero exit on failure); flags schema/provenance problems |
| 4 | `erpqa generate-sql <project_path>` | approved `DB_ASSERTION` rule YAML in `rules/` | SELECT-only `.sql` files in `generated/sql/`; skip/mark non-DB_ASSERTION; reject unsafe SQL with reason |
| 5 | `erpqa report <project_path>` | rules, validation outcomes, generated SQL, entity/flow maps | Markdown report(s) in `reports/` |
| 6 | `erpqa handoff <project_path>` | `reports/`, `rules/`, `entity_map.yaml`, `flow_map.yaml`, `feedback/` | `handoff/fix_handoff.md`, `handoff/codex_fix_prompt.md`; creates `feedback/feedback_items.yaml` + `feedback/PM_FEEDBACK_TEMPLATE.md` if missing |

See `ACCEPTANCE_CRITERIA.md` for the end-to-end pass conditions on the demo.

---

## 5. CLI Specification

Global conventions:
- CLI name: **`erpqa`**. Each command takes a **required positional** `<project_path>`.
- All managed state lives under `<project_path>/qa-context/`.
- **Exit codes:** `0` success; `1` user/validation error (e.g., schema failure, unsafe SQL, missing inputs); `2` usage error (bad args / missing path); `3` internal error.
- **Idempotency:** Re-running a command is safe. Re-generated derived artifacts (`source_inventory.md`, `.sql`, reports, handoff docs) are **overwritten**. Human-authored/approved artifacts (rule YAML, approved entity/flow edits, `feedback_items.yaml`) are **never silently overwritten**; templates are created **only if missing**.
- The toolkit MUST NOT write outside `<project_path>/qa-context/` and MUST NOT modify target ERP source files.

### 5.1 `erpqa init <project_path>`
- **Synopsis:** Scaffold the `qa-context/` workspace.
- **Inputs:** `<project_path>` (must exist; must be a directory).
- **Outputs / side effects:** Creates the full `qa-context/` tree (§6) with stub `project_manifest.yaml` and empty `entity_map.yaml` / `flow_map.yaml`. Creates `rules/`, `generated/sql/`, `reports/`, `feedback/`, `handoff/`.
- **Idempotency:** Existing files are preserved; missing scaffold pieces are created. Never destroys user content.
- **Failure modes:** path missing/not a directory → exit `2`; unwritable path → exit `1`.

### 5.2 `erpqa intake <project_path>`
- **Synopsis:** Walk the project folder, classify sources, build the inventory.
- **Inputs:** `<project_path>` containing ERP project files; requires `qa-context/` (auto-init if absent or error clearly — implementation choice documented in `ARCHITECTURE.md`).
- **Outputs / side effects:** Writes `source_inventory.md` (human-readable classified listing) and populates `project_manifest.yaml` (modules + classified inventory). Each inferred classification carries the provenance trio (§7).
- **Idempotency:** Regenerates `source_inventory.md` and refreshes the inferred portion of `project_manifest.yaml` on each run (overwrite of derived sections).
- **Failure modes:** empty/unreadable project → exit `1` with explanation.

### 5.3 `erpqa validate <project_path>`
- **Synopsis:** Validate all YAML against required schemas and report problems.
- **Inputs:** `project_manifest.yaml`, `entity_map.yaml`, `flow_map.yaml`, `rules/*.yaml`, `feedback/feedback_items.yaml` (if present).
- **Checks:** required fields present; enum values legal (confidence, severity, verification_type); provenance trio present on every inferred item; cross-references resolvable (rule → entities/tables/flow); SQL strings on `DB_ASSERTION` rules pass the **SQL safety model** (§10).
- **Outputs / side effects:** Human-readable validation summary to stdout (and optionally `reports/validation_report.md`). **No** mutation of inputs.
- **Exit codes:** `0` if all valid; `1` if any schema/safety/reference problem.
- **Failure modes:** missing required file → reported as a validation problem, not a crash.

### 5.4 `erpqa generate-sql <project_path>`
- **Synopsis:** Convert approved `DB_ASSERTION` rules into SELECT-only `.sql` assertion files.
- **Inputs:** `rules/*.yaml`.
- **Behavior:**
  - For each rule with `verification_type: DB_ASSERTION` whose `sql` passes the safety checker → write `generated/sql/<rule_id>.sql`.
  - Non-`DB_ASSERTION` rules → **skipped** and noted.
  - Rules failing the safety checker → **rejected** with a clear reason; no file written.
  - Rules with no safe SQL → marked `NEEDS_SCHEMA_CONFIRMATION` (no SQL emitted).
- **Outputs / side effects:** `.sql` files in `generated/sql/` (overwritten on rerun). A generation summary to stdout.
- **First release constraint:** Generated SQL is **never executed** against any DB.
- **Exit codes:** `0` if generation completes (even with skips/marks); `1` if a rule’s declared SQL fails safety and the run is configured to treat that as fatal (default: report and continue, exit `0`; document chosen default in `ARCHITECTURE.md`).

### 5.5 `erpqa report <project_path>`
- **Synopsis:** Build human-reviewable Markdown QA report(s).
- **Inputs:** rules, validation outcomes, generated SQL inventory, `entity_map.yaml`, `flow_map.yaml`.
- **Outputs / side effects:** Markdown file(s) in `reports/` (e.g., `qa_report.md`) summarizing entities, flows, rules by severity/verification_type, items needing human confirmation, and SQL generation status. Overwritten on rerun.
- **Exit codes:** `0` normally; `1` if required inputs are missing.

### 5.6 `erpqa handoff <project_path>`
- **Synopsis:** Turn QA findings + PM feedback into AI-readable fix-handoff documents.
- **Inputs:** `reports/`, `rules/`, `entity_map.yaml`, `flow_map.yaml`, `feedback/` (`feedback_items.yaml`).
- **Outputs / side effects:** Writes `handoff/fix_handoff.md` and `handoff/codex_fix_prompt.md` (overwritten). Creates `feedback/feedback_items.yaml` and `feedback/PM_FEEDBACK_TEMPLATE.md` **only if missing**.
- **Constraint:** Generated handoff docs target the *separate* ERP codebase; this toolkit **never** modifies that code.
- **Exit codes:** `0` normally; `1` if required inputs are missing.

---

## 6. qa-context Layout

```
<project_path>/qa-context/
  project_manifest.yaml          # project meta + classified source inventory + module list
  source_inventory.md            # human-readable classified listing of all source files
  entity_map.yaml                # inferred ERP entities (tables, keys, columns) + provenance
  flow_map.yaml                  # inferred business flows (steps, side effects) + provenance
  rules/                         # human-reviewable data-integrity rule YAML files (one per rule or grouped)
  generated/
    sql/                         # SELECT-only .sql assertion files (one per DB_ASSERTION rule)
  reports/                       # generated Markdown QA reports (qa_report.md, validation_report.md)
  feedback/
    feedback_items.yaml          # structured PM/QA feedback items (created if missing)
    PM_FEEDBACK_TEMPLATE.md      # template a non-dev PM fills in (created if missing)
  handoff/
    fix_handoff.md               # AI-readable fix handoff for a coding agent
    codex_fix_prompt.md          # ready-to-paste prompt for Codex/Claude to investigate & fix
```

---

## 7. Data Model / YAML Schemas

### 7.0 Universal Provenance Trio (semantics)
Every **inferred** ERP item (entity, flow, rule, feedback item, and inventory classifications) MUST carry:

| Field | Type | Allowed values | Meaning |
|-------|------|----------------|---------|
| `source` | string | free text | Where the inference came from (file path, doc name, "inferred from schema+screen spec"). Traceability. |
| `confidence` | enum | `high` \| `medium` \| `low` | LLM/heuristic certainty in the inference. |
| `needs_human_confirmation` | boolean | `true` \| `false` | Whether a human must approve before the item is trusted for business meaning / release decisions. |

Rule of thumb: `low`/`medium` confidence SHOULD set `needs_human_confirmation: true`. Validation (§5.3) flags any inferred item missing the trio.

### 7.1 `entity_map.yaml`
Required fields per entity:

| Field | Type | Notes |
|-------|------|-------|
| `entity` | string | Logical entity name |
| `physical_table` | string | Generic placeholder table name |
| `module` | string | Owning module |
| `type` | string | e.g., master / transaction / movement |
| `primary_key` | list[string] | PK column(s) |
| `important_columns` | list[string] | Key business columns |
| `status_columns` | list[string] | Status/state columns |
| `quantity_columns` | list[string] | Quantity columns |
| `amount_columns` | list[string] | Monetary columns |
| `source` | string | provenance |
| `confidence` | enum | `high`/`medium`/`low` |
| `needs_human_confirmation` | boolean | provenance |

```yaml
entities:
  - entity: InventoryMovement
    physical_table: tbl_inventory_movement
    module: inventory
    type: movement
    primary_key: [movement_id]
    important_columns: [item_id, warehouse_id, movement_type, ref_doc_id]
    status_columns: [movement_status]
    quantity_columns: [quantity]
    amount_columns: []
    source: "inferred from db_schema/inventory.sql + screen_spec/inventory_receipt.md"
    confidence: high
    needs_human_confirmation: false
```

### 7.2 `flow_map.yaml`
Required fields per flow:

| Field | Type | Notes |
|-------|------|-------|
| `flow_id` | string | Stable id |
| `name` | string | Human name |
| `module` | string | Owning module |
| `steps` | list[string] | Ordered steps |
| `trigger_screen` | string | Screen that initiates |
| `user_action` | string | The action performed |
| `related_entities` | list[string] | Entity names |
| `affected_tables` | list[string] | Physical tables touched |
| `status_transitions` | list[string] | State changes |
| `downstream_side_effects` | list[string] | Cross-module effects |
| `source` / `confidence` / `needs_human_confirmation` | provenance trio | |

```yaml
flows:
  - flow_id: inv_receipt_confirm
    name: Confirm Goods Receipt
    module: inventory
    steps:
      - "Open receipt screen"
      - "Confirm receipt"
      - "System creates inventory movement"
    trigger_screen: inventory_receipt
    user_action: confirm_receipt
    related_entities: [InventoryMovement, PurchaseOrder]
    affected_tables: [tbl_inventory_movement, tbl_purchase_order]
    status_transitions: ["receipt: draft -> confirmed"]
    downstream_side_effects: ["stock quantity increases", "PO received_qty updated"]
    source: "inferred from screen_spec/inventory_receipt.md"
    confidence: medium
    needs_human_confirmation: true
```

### 7.3 Rule YAML (`rules/*.yaml`)
Required fields per rule:

| Field | Type | Allowed values / notes |
|-------|------|------------------------|
| `rule_id` | string | Stable id |
| `name` | string | Human name |
| `module` | string | Owning module |
| `flow` | string | `flow_id` reference |
| `severity` | enum | `BLOCKER` \| `MAJOR` \| `MINOR` |
| `verification_type` | enum | `DB_ASSERTION` \| `API_ASSERTION` \| `UI_ASSERTION` \| `MANUAL` |
| `description` | string | What the rule checks |
| `expected_result` | string | Expected business outcome |
| `required_entities` | list[string] | Entity names |
| `required_tables` | list[string] | Physical tables |
| `sql` | string \| null | SELECT-only; returns rows **only when violated**; `null` / omitted if `NEEDS_SCHEMA_CONFIRMATION` |
| `source` / `confidence` / `needs_human_confirmation` | provenance trio | |

```yaml
rules:
  - rule_id: inv_no_negative_stock
    name: Stock quantity must not be negative
    module: inventory
    flow: inv_receipt_confirm
    severity: BLOCKER
    verification_type: DB_ASSERTION
    description: "On-hand stock must never be negative for any item/warehouse."
    expected_result: "Zero rows: no negative on-hand balances exist."
    required_entities: [InventoryBalance]
    required_tables: [tbl_inventory_balance]
    sql: |
      SELECT item_id, warehouse_id, on_hand_qty
      FROM tbl_inventory_balance
      WHERE on_hand_qty < 0;
    source: "rule pack: inventory integrity"
    confidence: high
    needs_human_confirmation: false
```

### 7.4 Feedback Item YAML (`feedback/feedback_items.yaml`)
Required fields per item:

| Field | Type | Notes |
|-------|------|-------|
| `feedback_id` | string | Stable id |
| `title` | string | Short title |
| `module` | string | Affected module |
| `related_flow` | string | `flow_id` |
| `related_rule_id` | string | `rule_id` (if any) |
| `severity` | enum | `BLOCKER`/`MAJOR`/`MINOR` |
| `user_observed_behavior` | string | What the PM saw |
| `expected_behavior` | string | What should happen |
| `actual_behavior` | string | What actually happened |
| `reproduction_steps` | list[string] | Steps |
| `evidence` | string/list | Screenshots, doc refs, record ids |
| `affected_records` | string/list | Example record identifiers |
| `suspected_area` | string | Likely module/code path |
| `ai_fix_instruction` | string | Direction for the coding agent |
| `validation_after_fix` | string | How to re-verify |
| `source` / `confidence` / `needs_human_confirmation` | provenance trio | |

```yaml
feedback_items:
  - feedback_id: fb_001
    title: "Shipment cancel did not restore stock"
    module: inventory
    related_flow: shipment_cancel
    related_rule_id: inv_shipment_cancel_restores_stock
    severity: MAJOR
    user_observed_behavior: "After cancelling a shipment, stock stayed reduced."
    expected_behavior: "Cancelling a confirmed shipment restores stock."
    actual_behavior: "Stock unchanged after cancel."
    reproduction_steps:
      - "Confirm a shipment"
      - "Cancel the shipment"
      - "Check on-hand balance"
    evidence: "screenshot_shipment_cancel.png"
    affected_records: ["shipment_id=SH-1001"]
    suspected_area: "inventory shipment-cancel handler"
    ai_fix_instruction: "Ensure cancel path emits a reversing inventory movement."
    validation_after_fix: "Re-run rule inv_shipment_cancel_restores_stock; expect 0 rows."
    source: "PM feedback session"
    confidence: medium
    needs_human_confirmation: true
```

---

## 8. Source Inventory & Classification

`intake` walks `<project_path>` (excluding `qa-context/`) and classifies each file into one of:

| Category | Examples |
|----------|----------|
| `docs` | requirements, business docs, manuals |
| `db_schema` | `.sql` DDL, schema dumps, ERD exports |
| `api_specs` | OpenAPI/Swagger, API markdown |
| `screen_specs` | screen/page specifications, wireframe notes |
| `backend` | server source files |
| `frontend` | UI source files |

`source_inventory.md` records, per item: relative path, detected **category**, the **module** it likely belongs to, and the provenance trio (`source`, `confidence`, `needs_human_confirmation`). Unclassifiable files are listed with `confidence: low` and `needs_human_confirmation: true`. The classified inventory + module list is mirrored into `project_manifest.yaml` for machine consumption.

---

## 9. Rule System

### Severity
`BLOCKER` (release-stopping data-integrity violation) > `MAJOR` (serious but possibly releasable with sign-off) > `MINOR` (low impact / cosmetic).

### `verification_type` semantics
| Type | Meaning (first release) |
|------|--------------------------|
| `DB_ASSERTION` | Verified by a SELECT-only SQL assertion (SQL **generated**, not executed). |
| `API_ASSERTION` | Intended for API checks — **declared only**; no API test generation now. |
| `UI_ASSERTION` | Intended for UI checks — **declared only**; no UI automation now. |
| `MANUAL` | A human must verify; no automation. |

### `NEEDS_SCHEMA_CONFIRMATION` state
When a `DB_ASSERTION` rule cannot be expressed as safe SQL (missing/ambiguous schema), it is marked `NEEDS_SCHEMA_CONFIRMATION` instead of emitting SQL. Reports surface these for human follow-up.

### Internal rule format & future export
The internal rule format (§7.3) is deliberately structured so it can **later** (not now) be exported to: raw SQL assertions, Great Expectations expectations, SodaCL checks, dbt tests, Schemathesis configs, Playwright skeletons, GraphWalker graph models, AltWalker models. Export mechanics and the full target list live in **`docs/integrations.md`** — see that doc; do not duplicate it here. Reusable starter rules live under `rule_packs/`.

---

## 10. SQL Safety Model

Applied by `validate` and `generate-sql` to every `DB_ASSERTION` rule’s `sql`.

1. **Allow-list:** Only `SELECT` statements are permitted.
2. **Reject keyword list (verbatim):** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`, `MERGE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`.
3. **Reject unsafe multiple statements:** stacked/semicolon-separated statements are rejected.
4. **Reject hidden destructive content:** SQL that hides destructive statements via comments or stacked queries is rejected.
5. **"Rows only when violations exist" convention:** an assertion must return rows **only** when a violation is present; zero rows = pass.
6. **Fallback:** if no safe SQL is possible, mark the rule `NEEDS_SCHEMA_CONFIRMATION` (emit no `.sql`).
7. **No execution:** the first release **does not execute** SQL against any real/production DB; it only **generates and safety-checks** SQL.

Each rejection MUST produce a **clear, specific reason**. See `CONSTRAINTS.md` for the authoritative restatement of these guardrails.

---

## 11. Feedback-to-Fix Handoff

### PM workflow
1. A non-developer PM fills in `feedback/PM_FEEDBACK_TEMPLATE.md` with rough QA feedback.
2. The toolkit structures that into `feedback/feedback_items.yaml` (schema §7.4).
3. `erpqa handoff` reads QA artifacts + feedback and emits handoff docs.

### Inputs read by `handoff`
`qa-context/reports/`, `qa-context/rules/`, `qa-context/entity_map.yaml`, `qa-context/flow_map.yaml`, `qa-context/feedback/`.

### Generated documents
- `handoff/fix_handoff.md` — structured, AI-readable handoff.
- `handoff/codex_fix_prompt.md` — ready-to-paste prompt for a coding agent.
- (Created if missing: `feedback/feedback_items.yaml`, `feedback/PM_FEEDBACK_TEMPLATE.md`.)

### The handoff MUST enable a coding agent to:
1. Locate the likely affected module / code path.
2. Understand expected vs actual behavior.
3. Inspect related rules and SQL assertions.
4. Implement a fix **in the target ERP codebase**.
5. Add/update tests.
6. Rerun validation after the fix.

### Hard constraint
The toolkit **MUST NEVER auto-modify** target ERP application code. It only produces handoff documents/prompts.

---

## 12. Skill Spec Files

Codex must create these **Markdown SKILL.md specs** (specs for *future* agents — describe purpose, inputs, outputs, steps, guardrails, and human-approval points). Do **not** implement agent runtimes.

| File | Describes |
|------|-----------|
| `skills/erp-intake/SKILL.md` | Folder walk, classification, `source_inventory.md` / manifest building |
| `skills/erp-domain-modeler/SKILL.md` | Producing `entity_map.yaml` and `flow_map.yaml` from sources |
| `skills/erp-rule-generator/SKILL.md` | Proposing human-reviewable data-integrity rules |
| `skills/erp-test-generator/SKILL.md` | Turning approved `DB_ASSERTION` rules into SELECT-only SQL |
| `skills/erp-report-generator/SKILL.md` | Building Markdown QA reports |
| `skills/erp-fix-handoff/SKILL.md` | Structuring feedback into fix-handoff docs |

Each SKILL.md must state: **purpose, inputs, outputs, steps, guardrails, human-approval points**.

---

## 13. Demo Project

`examples/pipe-manufacturing-demo/` is a minimal, **generic-placeholder** pipe-manufacturing ERP project. It must include enough docs / DB schema / screen specs across a few modules (inventory, purchase, production) for the full pipeline to run end-to-end. **Generic placeholder tables only** (e.g., `tbl_inventory_movement`, `tbl_inventory_balance`, `tbl_purchase_order`, `tbl_production_result`, `tbl_work_order`). **Never** use real company names.

### Example rules the demo should exercise (generic tables)
**Inventory**
- Confirmed receipt must create an inventory movement.
- Stock quantity must not be negative.
- Shipment confirmation must decrease stock.
- Shipment cancellation must restore stock.

**Purchase**
- Confirmed goods receipt must update purchase order received quantity.
- A cancelled purchase order must not allow receipt.

**Production**
- A completed production result must create an inventory movement.
- Good qty + defect qty must equal total output qty.
- Production output must not exceed work-order quantity unless explicitly allowed.

See `ACCEPTANCE_CRITERIA.md` for the demo end-to-end pass requirement.

---

## 14. Repository Structure

```
erpqa/
  cli.py            # erpqa CLI entry point (init/intake/validate/generate-sql/report/handoff)
  core/             # qa-context model, YAML schemas/validation, SQL safety checker
  adapters/         # source intake / classification adapters
  generators/       # rule -> SQL, future-export scaffolding
  reporters/        # Markdown report + handoff doc generation
docs/
  integrations.md   # future export targets (GE, SodaCL, dbt, Schemathesis, Playwright, GraphWalker, AltWalker, ...)
skills/             # the six SKILL.md spec files
rule_packs/         # reusable starter rule YAML packs
examples/
  pipe-manufacturing-demo/   # bundled demo project (generic placeholder tables)
```

(Plus top-level docs: `README.md`, `SPEC.md`, `CONSTRAINTS.md`, `ACCEPTANCE_CRITERIA.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and a `tests/` suite for basic coverage.)

---

## 15. Glossary

| Term | Definition |
|------|------------|
| **qa-context** | The managed workspace under `<project_path>/qa-context/` holding all toolkit artifacts. |
| **Provenance trio** | `source` + `confidence` + `needs_human_confirmation`, required on every inferred item. |
| **Entity map** | `entity_map.yaml`: inferred ERP entities/tables and their key columns. |
| **Flow map** | `flow_map.yaml`: inferred business flows, transitions, and side effects. |
| **Rule** | A human-reviewable data-integrity check (§7.3) with a severity and verification type. |
| **DB_ASSERTION** | A rule verified by a SELECT-only SQL assertion (generated, not executed in v1). |
| **NEEDS_SCHEMA_CONFIRMATION** | State for a DB_ASSERTION rule that cannot yet be expressed as safe SQL. |
| **SQL safety model** | The allow-list / reject-list checker ensuring only safe SELECTs are emitted (§10). |
| **Fix handoff** | AI-readable docs (`fix_handoff.md`, `codex_fix_prompt.md`) directing a coding agent to fix the *target* ERP code. |
| **Target ERP codebase** | The separate application under QA; this toolkit reads its files but never modifies its code. |
| **Rule pack** | A reusable bundle of starter rules under `rule_packs/`. |
| **PM** | Project/product manager — the primary non-developer user. |
