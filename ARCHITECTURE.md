# ERP QA Kit — ARCHITECTURE

> Architecture source of truth for the AI coding agent (Codex).
> Read alongside sibling docs: **SPEC.md** (behavioral spec), **CONSTRAINTS.md**
> (hard rules), **ROADMAP.md** (sequencing), and **docs/integrations.md**
> (exporter targets). This file describes *modules, responsibilities, data
> flow, and extension points* — it does NOT contain real implementation code.

---

## 1. Architectural Overview

ERP QA Kit is a **local-file-based, offline, AI-assisted ERP data-integrity QA
framework**. The architecture is organized around one non-negotiable separation
of concerns:

```
   LLM PROPOSES   ─────►   DETERMINISTIC CODE VERIFIES   ─────►   HUMAN APPROVES
   (structure,            (schema validation,                   (business meaning,
    mappings,              SQL safety checking,                  severity, release,
    flows, rules,          report/handoff                        final fixes)
    fix drafts)            generation)
```

| Concern | Who | Where it lives | LLM allowed? |
|---|---|---|---|
| Discover structure, infer entities/flows/rules, draft handoffs | **LLM (PROPOSE)** | `skills/` specs guide an external agent; outputs land in `qa-context/` as YAML/MD | YES (authoring time) |
| Validate YAML, check SQL safety, emit provenance, render reports/handoffs | **Deterministic code (VERIFY)** | `core/`, `generators/`, `reporters/` | **NO — must run without any LLM at runtime** |
| Confirm business meaning, severity, release readiness, apply real fixes | **Human (APPROVE)** | `needs_human_confirmation` flags, `feedback/`, PM templates | N/A |

**Mandatory determinism boundary:** Everything reachable from the `erpqa` CLI at
runtime (`validate`, `generate-sql`, `report`, `handoff`) MUST be deterministic
and offline. An LLM may help a human *author* the YAML inputs (guided by
`skills/`), but the **verification path never calls an LLM and never executes
against a database** in the first release.

### High-level pipeline

```
 ┌────────┐   ┌────────┐   ┌──────────┐   ┌──────────────┐   ┌────────┐   ┌─────────┐
 │  init  │──►│ intake │──►│ validate │──►│ generate-sql │──►│ report │──►│ handoff │
 └────────┘   └────────┘   └──────────┘   └──────────────┘   └────────┘   └─────────┘
     │            │             │                │                │            │
 writes        reads          reads           reads            reads        reads
 scaffold      TARGET/        entity_map       rules/*.yaml     reports      feedback/
 +manifest     (READ-ONLY)    flow_map         (DB_ASSERTION)   inputs       +findings
               writes         rules/*.yaml     writes           writes       writes
               source_        (deterministic   generated/sql/   reports/     handoff/
               inventory.md   schema check)    + safety gate    *.md         fix_handoff.md
               entity_map     exit-code                                      codex_fix_prompt.md
               flow_map       contract
```

`TARGET/` = the target ERP project folder. It is **read-only**. The CLI only
ever writes under `<project_path>/qa-context/`.

Full pipeline order (each command takes `<project_path>`):

```
erpqa init <p>  →  erpqa intake <p>  →  erpqa validate <p>
                →  erpqa generate-sql <p>  →  erpqa report <p>  →  erpqa handoff <p>
```

---

## 2. Layered Module Map

```
erpqa/
  cli.py        ── thin command dispatch
  core/         ── domain models, schemas, validation, SQL safety, provenance  [LLM-FREE]
  adapters/     ── read-only source intake & classification
  generators/   ── SQL assertion generation; feedback→handoff generation
  reporters/    ── Markdown report generation
```

| Module | MUST do | MUST NOT do |
|---|---|---|
| **`erpqa/cli.py`** | Parse args; dispatch the 6 commands; resolve `<project_path>`; enforce pipeline preconditions; map results to exit codes. | Contain business logic, parsing of ERP sources, or SQL generation. No LLM calls. |
| **`core/`** | Define the 4 domain models + provenance mixin + enums; deterministic YAML schema validation; SQL safety checker; provenance helpers; the `NEEDS_SCHEMA_CONFIRMATION` state. | **Call an LLM. Touch the network. Execute SQL.** Write outside `qa-context/`. Read the target folder (that's adapters' job). |
| **`adapters/`** | Read-only ingestion of the target ERP folder; classify sources into 6 categories; produce `source_inventory.md` and seed `project_manifest.yaml`; assign provenance. | Modify/write into the target folder. Decide business semantics on its own (those are proposals needing human confirmation). |
| **`generators/`** | Turn `DB_ASSERTION` rules into SQL via `core` templates; route every SQL string through the `core` safety gate; turn feedback+findings into `fix_handoff.md` and `codex_fix_prompt.md`. | Bypass the safety checker. Emit unsafe SQL. Auto-modify target ERP code. |
| **`reporters/`** | Render Markdown reports from validated/generated artifacts; summarize coverage, severity, confirmation needs. | Re-derive or mutate domain data; call an LLM at runtime. |

> `core/` is the determinism kernel. If any item in `core/` needs an LLM, it is
> misplaced — it belongs in a `skills/` spec executed at authoring time, not
> runtime.

---

## 3. Core Domain Model

Conceptual schemas (illustrative pseudostructure, **not** implementation). Each
inferred object carries the **provenance trio**.

### Shared mixin — Provenance trio

```
Provenance (mixin):
    source                     : str          # where this was inferred from
    confidence                 : high | medium | low
    needs_human_confirmation   : bool
```

### Enums

```
Severity          = BLOCKER | MAJOR | MINOR
VerificationType  = DB_ASSERTION | API_ASSERTION | UI_ASSERTION | MANUAL
```

### Entity

```
Entity(Provenance):
    entity              : str
    physical_table      : str
    module              : str
    type                : str
    primary_key         : str | list[str]
    important_columns   : list[str]
    status_columns      : list[str]
    quantity_columns    : list[str]
    amount_columns      : list[str]
```

### Flow

```
Flow(Provenance):
    flow_id                 : str
    name                    : str
    module                  : str
    steps                   : list[str]
    trigger_screen          : str
    user_action             : str
    related_entities        : list[str]       # → Entity.entity
    affected_tables         : list[str]
    status_transitions      : list[str]
    downstream_side_effects : list[str]
```

### Rule

```
Rule(Provenance):
    rule_id           : str
    name              : str
    module            : str
    flow              : str                    # → Flow.flow_id
    severity          : Severity
    verification_type : VerificationType
    description        : str
    expected_result   : str
    required_entities : list[str]
    required_tables   : list[str]
    sql               : str | null             # only for DB_ASSERTION
```

### FeedbackItem

```
FeedbackItem(Provenance):
    feedback_id            : str
    title                  : str
    module                 : str
    related_flow           : str               # → Flow.flow_id
    related_rule_id        : str               # → Rule.rule_id
    severity               : Severity
    user_observed_behavior : str
    expected_behavior      : str
    actual_behavior        : str
    reproduction_steps     : list[str]
    evidence               : str
    affected_records       : str
    suspected_area         : str
    ai_fix_instruction     : str
    validation_after_fix   : str
```

### The `NEEDS_SCHEMA_CONFIRMATION` state

A first-class outcome (not an exception) emitted by SQL generation when no
*provably safe* SELECT can be produced for a `DB_ASSERTION` rule (missing/unknown
schema). It marks the rule's generated artifact as blocked-pending-human and is
surfaced in reports and handoff. It is distinct from a validation error.

---

## 4. Adapters / Intake Subsystem

**Responsibility:** read-only ingestion of the target ERP folder and
classification of its contents into proposed structure.

```
        TARGET ERP FOLDER (READ-ONLY)
                  │  scan (no writes)
                  ▼
        ┌──────────────────────┐
        │   adapters/ intake   │
        │  classify into 6     │
        │  source categories   │
        └──────────────────────┘
                  │  writes ONLY to qa-context/
                  ▼
   source_inventory.md   project_manifest.yaml   entity_map.yaml(seed)   flow_map.yaml(seed)
```

### Six source categories

| # | Category | Typical inputs |
|---|---|---|
| 1 | Docs | requirements, specs, READMEs, business docs |
| 2 | DB schema | DDL, migrations, ORM models, ERDs |
| 3 | API specs | OpenAPI/Swagger, route definitions |
| 4 | Screen specs | UI/screen design docs, wireframes |
| 5 | Backend | server source (read for structure only) |
| 6 | Frontend | client source (read for structure only) |

**Classification approach:** path/extension + lightweight content heuristics to
bucket each discovered file into a category and record it. Semantic
inference (which table is which entity, which screen triggers which flow) is a
**proposal** — every inferred item gets a provenance trio, and uncertain ones get
`needs_human_confirmation: true`.

**Outputs:**
- `source_inventory.md` — human-readable catalog of discovered sources by category, with coverage notes.
- `project_manifest.yaml` — machine-readable project descriptor (target root, detected modules, category counts, intake metadata) used by later stages.
- Seeds of `entity_map.yaml` / `flow_map.yaml` may be proposed for human refinement (LLM-assisted at authoring time via `skills/intake` + `skills/domain-modeler`).

**Invariant:** the target folder is opened read-only; all writes go to
`qa-context/`. No file under `TARGET/` is ever created or modified.

---

## 5. Validation Subsystem

**Responsibility:** deterministic schema validation of every `qa-context/` YAML
artifact against the `core/` schemas. No LLM, no DB.

| YAML artifact | Validated against |
|---|---|
| `project_manifest.yaml` | manifest schema |
| `entity_map.yaml` | list of `Entity` (+ provenance trio) |
| `flow_map.yaml` | list of `Flow` (+ provenance trio) |
| `rules/*.yaml` | list of `Rule` (+ provenance trio; enum checks on severity/verification_type) |
| `feedback/feedback_items.yaml` | list of `FeedbackItem` (+ provenance trio) |

**Error reporting model:** collect *all* errors (not fail-fast), each as a
structured record: `{file, path/locator, code, message, severity}`. Cross-file
referential checks (e.g. `Rule.flow` → existing `Flow.flow_id`,
`Flow.related_entities` → existing `Entity.entity`) are included where both files
are present.

**Exit-code contract** (shared across deterministic commands):

| Exit | Meaning |
|---|---|
| 0 | All valid / clean |
| 1 | Validation error(s) — schema or referential |
| 2 | Usage / precondition error (e.g. pipeline stage run out of order, missing `qa-context/`) |
| 3 | Safety violation (used by `generate-sql`; see §6) |

> `NEEDS_SCHEMA_CONFIRMATION` is a *result state*, not a failure exit. A run that
> produces only confirmation-needed rules still exits 0 but flags them in output.

---

## 6. SQL Generation & Safety Subsystem

**Responsibility:** turn `DB_ASSERTION` rules into **assertion SQL** and pass
every produced statement through a deterministic **safety gate** before it is
written. No DB execution in the first release.

```
 rules/*.yaml (DB_ASSERTION)
        │
        ▼
 ┌──────────────────────┐     produces candidate SELECT (assertion semantics:
 │ generators/ sql gen  │     returns rows ONLY when a violation exists)
 └──────────────────────┘
        │ candidate SQL string
        ▼
 ┌──────────────────────┐   FAIL ─► reject (exit 3) / mark unsafe
 │ core/ SQL SAFETY GATE │
 └──────────────────────┘   no safe SQL possible ─► NEEDS_SCHEMA_CONFIRMATION
        │ PASS
        ▼
 generated/sql/<rule_id>.sql   (+ status recorded for report/handoff)
```

### Safety model (deterministic gate in `core/`)

1. **Allow-list:** statement must be a single `SELECT` (read-only).
2. **Deny keywords:** reject if any of —
   `INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, EXECUTE, MERGE, CREATE, REPLACE, GRANT, REVOKE, CALL`.
3. **Single statement:** reject multiple statements (statement-separator detection after comment/string stripping).
4. **Hidden destructive statements:** reject suspicious constructs that smuggle DML/DDL (e.g. via comments, stacked queries, encoded fragments).
5. **Assertion semantics:** generated SQL returns rows **only when violations exist** (a clean DB → empty result).
6. **No safe SQL:** if a provably-safe SELECT cannot be formed (unknown schema), emit `NEEDS_SCHEMA_CONFIRMATION` instead of writing a guessed statement.

**Design-level detection strategy:** tokenize after stripping comments and string
literals → uppercase keyword scan against the denylist → verify exactly one
top-level statement → re-scan for hidden/stacked separators → confirm leading
token is `SELECT`. The checker is pure/deterministic and unit-testable in
isolation; it never executes SQL.

**Output:** safe statements written to `generated/sql/<rule_id>.sql`; each rule's
generation status (`OK` / `UNSAFE` / `NEEDS_SCHEMA_CONFIRMATION` / `N/A —
non-DB`) is recorded for downstream stages.

---

## 7. Reporting Subsystem

**Responsibility:** render human-readable Markdown reports from validated and
generated artifacts. Deterministic, template-driven, no LLM.

**Summarized content:**
- Coverage: entities, flows, rules counts per module.
- Rule inventory by `severity` and `verification_type`.
- SQL generation status per rule (`OK` / `UNSAFE` / `NEEDS_SCHEMA_CONFIRMATION`).
- Provenance roll-up: how many items are `needs_human_confirmation: true`, grouped by confidence.
- Outstanding items requiring human approval.

**Templating approach:** static Markdown templates with simple field/loop
substitution over in-memory domain objects (no logic in templates). Output →
`qa-context/reports/*.md`.

---

## 8. Feedback-to-Fix Handoff Subsystem

**Responsibility:** convert rough PM feedback + QA findings into a structured
**fix handoff** that a downstream coding agent (Codex) can act on — *without
auto-modifying any target ERP code*.

```
 INPUTS                                   OUTPUTS (qa-context/handoff/)
 ─────────────────────────────────       ──────────────────────────────
 feedback/feedback_items.yaml      ─┐
 feedback/PM_FEEDBACK_TEMPLATE.md  ─┤──► generators/ handoff ──► fix_handoff.md
 rules/*.yaml  (related_rule_id)   ─┤                           codex_fix_prompt.md
 flow_map.yaml (related_flow)      ─┤
 reports/*.md  (QA findings)       ─┘
```

**Flow:** PM fills `PM_FEEDBACK_TEMPLATE.md` (rough, human language); items are
captured in `feedback_items.yaml` as `FeedbackItem`s (provenance-tagged, LLM may
assist authoring). The deterministic generator joins each item with its
`related_rule_id` / `related_flow` and QA findings to emit:

- **`fix_handoff.md`** — human-and-agent-readable: per-item problem, expected vs actual, reproduction, evidence, affected records, suspected area, and validation-after-fix.
- **`codex_fix_prompt.md`** — a ready-to-paste prompt for the downstream coding agent.

**Six AI-fix capabilities** are structured into the output (each `FeedbackItem`
field maps to one), giving the downstream agent: (1) the observed problem,
(2) expected behavior, (3) actual behavior, (4) reproduction steps,
(5) the targeted fix instruction (`ai_fix_instruction` + `suspected_area`), and
(6) the post-fix validation (`validation_after_fix`, tied back to the rule).

**No-auto-modify boundary:** this subsystem produces *drafts and prompts only*.
It never edits the target ERP code. A human reviews the handoff and a separate
agent/human performs the actual fix.

---

## 9. Internal Rule IR & Exporter Extension Points

The `Rule` schema (§3) is the **stable, tool-agnostic Intermediate
Representation (IR)**. It is the contract future exporters target. **No exporters
are built in the first release** — this section defines *where* they will attach.

```
                         ┌──────────────────────────┐
   Rule IR (stable) ────►│  Exporter interface       │────► (future) tool-specific output
   Flow IR (stable) ────►│  export(items) -> artifact │
                         └──────────────────────────┘
                              ▲   NOT IMPLEMENTED NOW
```

**Exporter interface concept** (design placeholder, not built):

```
Exporter (protocol):
    name : str
    def export(items: list[Rule] | list[Flow]) -> artifact   # pure, deterministic
```

Attachment map (targets enumerated in **docs/integrations.md**):

| Future tool | Class | Attaches to | Driven by |
|---|---|---|---|
| Raw SQL | DB quality | Rule IR | `sql` / DB_ASSERTION |
| Great Expectations | DB quality | Rule IR | DB_ASSERTION |
| SodaCL | DB quality | Rule IR | DB_ASSERTION |
| dbt tests | DB quality | Rule IR | DB_ASSERTION |
| Schemathesis | API | Rule IR | API_ASSERTION rules + API specs |
| Playwright | UI/flow | flow_map + Rule IR | UI_ASSERTION rules |
| GraphWalker | Model-based/flow | flow_map (states/transitions) | Flow IR |
| AltWalker | Model-based/flow | flow_map (states/transitions) | Flow IR |

> Rule designers MUST keep the IR tool-agnostic: no exporter-specific fields leak
> into `Rule`/`Flow`. Exporters adapt the IR outward; the IR never bends inward
> toward a single tool. **NOT built now** — see ROADMAP.md.

---

## 10. Skills Layer

`skills/` contains **six `SKILL.md` specifications** describing how an external
agent should *propose* artifacts. In the first release these are **markdown
specs, not runtime code** — they guide authoring-time LLM behavior; the CLI does
not load or execute them.

| Skill | Proposes | Feeds |
|---|---|---|
| `intake` | source classification, inventory | `source_inventory.md`, manifest |
| `domain-modeler` | entities & flows | `entity_map.yaml`, `flow_map.yaml` |
| `rule-generator` | rules from flows/entities | `rules/*.yaml` |
| `test-generator` | assertion intent for DB_ASSERTION rules | rule `sql` proposals |
| `report-generator` | report framing | inputs to `reporters/` |
| `fix-handoff` | feedback capture & fix drafts | `feedback/`, `handoff/` |

The deterministic CLI consumes the *artifacts* these skills help produce — never
the skills themselves at runtime.

---

## 11. Data Flow & File Contracts

All inputs/outputs are under `<project_path>/qa-context/` unless noted.
`TARGET/` is the external ERP folder (read-only).

| Stage | Inputs | Outputs | Invariants |
|---|---|---|---|
| **init** | `<project_path>` | `qa-context/` scaffold + empty `project_manifest.yaml` | Idempotent; never overwrites existing user content; writes only under `qa-context/` |
| **intake** | `TARGET/` (read-only) | `source_inventory.md`, populated `project_manifest.yaml`, seeded `entity_map.yaml`/`flow_map.yaml` | Target folder never modified; every inferred item carries provenance trio |
| **validate** | `entity_map.yaml`, `flow_map.yaml`, `rules/*.yaml`, `feedback/feedback_items.yaml` | validation result + exit code | Deterministic; offline; no LLM; collects all errors; enforces enums & references |
| **generate-sql** | `rules/*.yaml` (DB_ASSERTION) | `generated/sql/<rule_id>.sql` + status | Every SQL passes safety gate; assertion-only SELECT; no DB execution; unsafe→reject, unknown schema→NEEDS_SCHEMA_CONFIRMATION |
| **report** | manifest, maps, rules, generated SQL status | `reports/*.md` | Deterministic render; summarizes coverage, severity, confirmation needs |
| **handoff** | `feedback/feedback_items.yaml`, `PM_FEEDBACK_TEMPLATE.md`, rules, flow_map, reports | `handoff/fix_handoff.md`, `handoff/codex_fix_prompt.md` | Drafts only; never modifies target ERP code; ties fixes back to rules |

---

## 12. Determinism, Safety & Boundaries

Restated hard rules (authoritative detail in **CONSTRAINTS.md**):

- **Deterministic & offline verification path.** `validate`, `generate-sql`, `report`, `handoff` run with **no LLM** and **no network** at runtime.
- **No DB execution / no DB connection** in the first release. SQL is generated and safety-checked, never run; no production DB access.
- **Never modify the target ERP code.** Intake reads the target folder read-only; all writes go to `qa-context/`. Handoff emits drafts/prompts, not edits.
- **SQL safety is a mandatory gate.** Allow-list SELECT only; denylist + single-statement + hidden-statement checks; assertion-only semantics.
- **Provenance everywhere.** Every inferred item carries `source` / `confidence` / `needs_human_confirmation`. Humans approve business meaning, severity, and release.
- **LLMs propose; deterministic code verifies; humans approve.** No part of the runtime verification path may depend on an LLM.

---

## 13. Directory Layout Reference

### Repository

```
erpqa/
  cli.py                     # CLI entrypoint / command dispatch (6 commands)
  core/                      # [LLM-FREE] domain models, schemas, validation,
                             #   SQL safety, provenance, enums, NEEDS_SCHEMA_CONFIRMATION
  adapters/                  # read-only intake & 6-category classification
  generators/                # SQL assertion gen (DB_ASSERTION) + feedback→handoff gen
  reporters/                 # Markdown report generation
docs/
  integrations.md            # exporter targets (future), not built now
skills/                      # six SKILL.md specs (markdown, not runtime code)
  intake/SKILL.md
  domain-modeler/SKILL.md
  rule-generator/SKILL.md
  test-generator/SKILL.md
  report-generator/SKILL.md
  fix-handoff/SKILL.md
rule_packs/                  # reusable rule templates (e.g. pipe-manufacturing starter)
examples/
  pipe-manufacturing-demo/   # worked example
ARCHITECTURE.md  SPEC.md  CONSTRAINTS.md  ROADMAP.md
```

### `qa-context/` (created under `<project_path>`)

```
qa-context/
  project_manifest.yaml      # machine-readable project descriptor
  source_inventory.md        # cataloged sources by category
  entity_map.yaml            # list[Entity]   (+ provenance trio)
  flow_map.yaml              # list[Flow]      (+ provenance trio)
  rules/                     # *.yaml  list[Rule] (+ provenance trio)
  generated/
    sql/                     # <rule_id>.sql  (safe SELECT assertions)
  reports/                   # *.md generated reports
  feedback/
    feedback_items.yaml      # list[FeedbackItem] (+ provenance trio)
    PM_FEEDBACK_TEMPLATE.md  # human PM input template
  handoff/
    fix_handoff.md           # structured fix handoff
    codex_fix_prompt.md      # ready-to-paste downstream-agent prompt
```

---

## 14. Future Architecture Notes  *(NOT-NOW — see ROADMAP.md)*

These are designed to attach **without rework** because the Rule/Flow IR and the
`qa-context/` contracts are stable. None are built in the first release.

| Out-of-scope item | How it attaches later | Why no rework |
|---|---|---|
| **Exporters** (Great Expectations, SodaCL, dbt, Schemathesis, Playwright, GraphWalker, AltWalker) | Implement the `Exporter` protocol (§9) over existing Rule/Flow IR | IR is tool-agnostic; exporters read it, don't change it |
| **Real DB connection/execution** | Add a runner that *executes* already-safety-checked `generated/sql/`; gated, opt-in | Generation + safety already separate from execution |
| **API test generation** | Realize `API_ASSERTION` rules via an API exporter | Slot exists in `VerificationType` enum |
| **Playwright UI impl** | Realize `UI_ASSERTION` rules + `flow_map` via a UI exporter | Flow IR already models steps/screens/transitions |
| **Model-based testing (GraphWalker/AltWalker)** | Emit models from `flow_map` status_transitions | Flow IR carries states & transitions |
| **Dashboard** | New reader over `qa-context/` reports/artifacts | Reporters are decoupled; artifacts are stable files |
| **GitHub Action / CI** | Wrap deterministic CLI; consume exit-code contract (§5) | Exit codes already standardized |
| **Auto crawler, SaaS/multi-tenant, plugin system** | Layer above the file contract; never inside `core/` | `core/` stays minimal, deterministic, LLM-free |

> Guardrail for all future work: nothing may introduce an LLM, a network call,
> or DB execution into the runtime verification path, and nothing may write into
> the target ERP folder. See CONSTRAINTS.md.
