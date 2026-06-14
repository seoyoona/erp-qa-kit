> **DRAFT** — This README is an early draft that doubles as a usage guide. It reflects the *intended design* of ERP QA Kit and will be refined during implementation (Codex will finalize packaging, exact command output, and any details marked as draft below). Commands are written to be copy-pasteable; if something here disagrees with the implemented behavior, the implemented behavior and the sibling docs (`SPEC.md`, `CONSTRAINTS.md`, `ACCEPTANCE_CRITERIA.md`) win.

# ERP QA Kit

**ERP QA Kit** is an open-source, local, file-based, AI-assisted framework for **ERP data-integrity QA**. It reads an ERP project folder, classifies what it finds (docs, DB schema, API specs, screen specs, backend, frontend), builds a QA context, models the ERP's entities and business flows, and proposes **human-reviewable data-integrity rules**. Approved rules of the right kind are turned into **SELECT-only SQL assertions**, results are written as **Markdown QA reports**, and QA findings plus a PM's plain-language feedback are converted into **AI-readable fix-handoff documents** for a coding agent (Codex/Claude) to act on.

**What it is NOT:** it is not a browser QA bot, not a dashboard, and not a one-off script. It does **not** click through your app, it does **not** show live charts, and it does **not** modify your ERP code. It is a repeatable pipeline that produces reviewable artifacts you keep in version control.

---

## 1. Who it's for & the problem it solves

ERP QA Kit is built for two audiences working together:

- **Non-developer PM / QA leads** — who own *business meaning*: which rules matter, how severe a violation is, whether a release can ship, and what "correct" actually means for the business.
- **Engineers** — who own the codebase, the data model, and the eventual fixes.

**The pilot context.** The first target is a **pipe-manufacturing ERP**: roughly **7 modules and ~140 pages**, heavy on CRUD and on **cross-module data consistency** (a receipt in one module must move stock correctly in another, a cancellation must restore what it undid, and so on). On a system this size, fully manual QA is too heavy to repeat every release, and browser smoke tests are flaky and don't actually check whether the *data* stayed consistent. ERP QA Kit focuses exactly on that gap: **deterministic, repeatable checks of data integrity**, proposed by an LLM but verified mechanically and approved by a human.

---

## 2. Core Principle

> **LLMs propose. Deterministic checks verify. Humans approve.**

- **LLMs propose** — entities, business flows, and candidate data-integrity rules are *inferred* by an LLM from your project. Everything inferred is a suggestion, never a fact.
- **Deterministic checks verify** — rules become **SELECT-only SQL assertions** that are mechanically safety-checked. The verification is code, not a model's opinion.
- **Humans approve** — a person (often a non-developer PM/QA lead) approves the **business meaning**, the **severity**, the **release decision**, and the **final fix**. Nothing is "trusted" until a human confirms it.

**The toolkit never modifies your ERP code.** It only *reads* the target project and *writes* artifacts into its own `qa-context/` folder. When a fix is needed, ERP QA Kit produces a **handoff document** — the actual code change is performed separately, by an AI coding agent (Codex/Claude) working in the target ERP codebase under human supervision.

---

## 3. How it works — the 6-stage pipeline

```
init  →  intake  →  validate  →  generate-sql  →  report  →  handoff
```

1. **init** — scaffold the `qa-context/` workspace (manifest stub, folders, templates).
2. **intake** — scan and classify the project's sources; write a source inventory and fill the manifest.
3. **validate** — check every `qa-context/` YAML file against its schema and report problems.
4. **generate-sql** — convert *approved* `DB_ASSERTION` rules into SELECT-only SQL assertions.
5. **report** — generate Markdown QA report(s) summarizing rules, coverage, and provenance.
6. **handoff** — turn reports + rules + maps + PM feedback into AI-readable fix-handoff documents.

Each command is a step you can re-run independently; the order above is the full end-to-end pipeline. It runs start to finish on the bundled demo at `examples/pipe-manufacturing-demo/`.

---

## 4. Installation

> **DRAFT — packaging is not final.** Codex will finalize the package name, entry point, and dependency list. The commands below show the *intended* developer install.

Requirements (intended):

- **Python 3.11+**
- A POSIX-ish shell (macOS / Linux; Windows via WSL should work)
- No database, no network access, and no API keys are required to run the demo pipeline.

Install from a local checkout in editable mode:

```bash
git clone <repo-url> erp-qa-kit
cd erp-qa-kit
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify the CLI is available:

```bash
erpqa --help
```

---

## 5. Quickstart on the demo

The repo ships a self-contained demo at `examples/pipe-manufacturing-demo/`. Run the full pipeline against it — every command takes a `<project_path>`:

```bash
# 0. Point an env var at the demo so the commands stay copy-pasteable
export DEMO=examples/pipe-manufacturing-demo

# 1. Scaffold the QA workspace
erpqa init $DEMO
#   → creates $DEMO/qa-context/ with a manifest stub, folders, and templates

# 2. Scan & classify the project's sources
erpqa intake $DEMO
#   → writes qa-context/source_inventory.md and fills qa-context/project_manifest.yaml

# 3. Validate all qa-context YAML against schemas
erpqa validate $DEMO
#   → prints problems (schema errors, missing provenance, etc.); fix before continuing

# 4. Convert approved DB_ASSERTION rules into SELECT-only SQL
erpqa generate-sql $DEMO
#   → writes safety-checked .sql files into qa-context/generated/sql/

# 5. Generate the Markdown QA report(s)
erpqa report $DEMO
#   → writes report(s) into qa-context/reports/

# 6. Produce the AI fix-handoff documents
erpqa handoff $DEMO
#   → writes qa-context/handoff/fix_handoff.md and qa-context/handoff/codex_fix_prompt.md
```

When you're done, everything produced lives under `examples/pipe-manufacturing-demo/qa-context/` — nothing outside that folder is touched.

---

## 6. The `qa-context/` folder

`init` creates a single workspace folder inside the target project. Everything ERP QA Kit produces lives here, and nowhere else:

```
qa-context/
├── project_manifest.yaml        # what this project is; modules, sources, settings (filled by intake)
├── source_inventory.md          # human-readable list of classified sources (written by intake)
├── entity_map.yaml              # inferred ERP entities (review before trusting)
├── flow_map.yaml                # inferred business flows (review before trusting)
├── rules/                       # data-integrity rules (severity + verification_type + provenance)
├── generated/
│   └── sql/                     # SELECT-only SQL assertions from approved DB_ASSERTION rules
├── reports/                     # Markdown QA report(s)
├── feedback/
│   ├── feedback_items.yaml      # structured PM observations
│   └── PM_FEEDBACK_TEMPLATE.md  # the plain-language template a PM fills in
└── handoff/
    ├── fix_handoff.md           # AI-readable fix brief for a coding agent
    └── codex_fix_prompt.md      # ready-to-paste prompt for Codex/Claude
```

---

## 7. Understanding provenance — why humans must review

ERP QA Kit assumes its own inferences can be wrong. Every inferred item — each entity, flow, and rule — carries three provenance fields:

- **`source`** — where the inference came from (which doc, schema file, spec, or code path).
- **`confidence`** — `high` | `medium` | `low`. How sure the model is.
- **`needs_human_confirmation`** — `true` | `false`. Whether a human must sign off before this item is trusted.

This is the mechanism behind the Core Principle. The LLM *proposes* an entity or rule and attaches its source and confidence; nothing is treated as correct until a human has reviewed it and the `needs_human_confirmation` gate is cleared. **Review `entity_map.yaml`, `flow_map.yaml`, and `rules/` before relying on anything downstream** — especially anything `low`-confidence or flagged for confirmation. Provenance is what makes the output auditable rather than a black box.

---

## 8. Rules & SQL safety

Each rule in `rules/` declares:

- **`severity`** — `BLOCKER` | `MAJOR` | `MINOR` (set/confirmed by a human; drives release decisions).
- **`verification_type`** — `DB_ASSERTION` | `API_ASSERTION` | `UI_ASSERTION` | `MANUAL`.

**In the first release, only `DB_ASSERTION` rules produce SQL.** The other verification types are recorded and reported, but their automation is future work.

### SQL safety guarantees

`generate-sql` is deliberately paranoid. For every `DB_ASSERTION` rule it produces SQL that:

- is **SELECT-only** — read-only by construction;
- is **rejected** if it contains any destructive or schema-changing keyword: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`, `MERGE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`;
- is **rejected** if it tries to smuggle in multiple or hidden statements;
- **returns rows only when a violation exists** — an empty result means the rule passed.

If a rule can't be expressed as safe SQL (for example, the schema is ambiguous), it is **not** force-fit into SQL — it is marked **`NEEDS_SCHEMA_CONFIRMATION`** and left for a human to resolve.

> **No database execution in the first release.** ERP QA Kit **generates and safety-checks** SQL but does **not** connect to, or run anything against, any database. Executing the assertions against a real DB is explicitly future work (see `ROADMAP.md`).

---

## 9. PM feedback → AI fix handoff

This is the workflow that lets a **non-developer PM/QA lead** drive fixes without writing code.

1. **Fill the template.** Open `qa-context/feedback/PM_FEEDBACK_TEMPLATE.md` (or `feedback/feedback_items.yaml`) and jot down rough observations in plain language — "shipment didn't reduce stock for module X," "cancelling a PO still let a receipt through," etc. No precision required.
2. **Run handoff.**
   ```bash
   erpqa handoff <project_path>
   ```
3. **Hand the output to a coding agent.** `handoff` combines the **reports**, the **rules**, the **entity/flow maps**, and your **feedback** into two artifacts:
   - `qa-context/handoff/fix_handoff.md` — a structured, AI-readable fix brief.
   - `qa-context/handoff/codex_fix_prompt.md` — a ready-to-paste prompt for Codex/Claude.

   Give these to an AI coding agent working **in the target ERP codebase**.

> **The toolkit itself never changes ERP code.** It only writes handoff docs. The actual edit happens elsewhere, performed by the coding agent with human oversight.

The handoff is written so the coding agent can:

1. **Locate** the affected module / code path.
2. **Understand** expected vs. actual behavior.
3. **Inspect** the related rules and SQL assertions.
4. **Implement** the fix in the target ERP codebase.
5. **Add or update** tests covering the fix.
6. **Rerun validation** to confirm the issue is resolved.

---

## 10. First release vs. not yet

**Included in the first release:**

- The `erpqa` CLI with all six commands (`init`, `intake`, `validate`, `generate-sql`, `report`, `handoff`).
- Source scan & classification + `source_inventory.md` and `project_manifest.yaml`.
- Inferred `entity_map.yaml` / `flow_map.yaml` with full provenance.
- Human-reviewable rules with `severity` and `verification_type`.
- SELECT-only SQL generation **with safety checks** for `DB_ASSERTION` rules (generation only, no execution).
- Markdown QA reports.
- PM feedback → `fix_handoff.md` + `codex_fix_prompt.md`.
- A working bundled demo at `examples/pipe-manufacturing-demo/`.

**Not yet (future work):**

- Executing SQL against a real database.
- Automation for `API_ASSERTION`, `UI_ASSERTION`, and model-based test generation.
- Exporters to Great Expectations, Soda Core, dbt tests, Schemathesis, Keploy, Playwright, GraphWalker, AltWalker.
- A dashboard / live UI.

See **`ROADMAP.md`** and **`docs/integrations.md`** for the full forward-looking plan.

---

## 11. Safety & boundaries

- **Local & offline.** Runs on local files; the demo pipeline needs no network and no API keys.
- **Target folder is read-only.** ERP QA Kit reads the target ERP project but never writes into or modifies its code.
- **Outputs are contained.** Everything generated lives under `qa-context/` and nowhere else.
- **SELECT-only SQL.** Generated assertions are read-only by construction and safety-checked against destructive keywords and hidden statements.
- **Human approval gates.** Business meaning, severity, release decisions, and final fixes always require human sign-off; provenance (`source` / `confidence` / `needs_human_confirmation`) keeps it auditable.

---

## 12. Project layout

```
erp-qa-kit/
├── README_DRAFT.md            # this file (draft)
├── SPEC.md                    # full functional specification
├── CONSTRAINTS.md             # hard constraints & non-goals
├── ACCEPTANCE_CRITERIA.md     # what "done" means for the first release
├── ARCHITECTURE.md            # internal design & module breakdown
├── ROADMAP.md                 # phased plan, including future work
├── docs/
│   └── integrations.md        # future exporters & integrations
└── examples/
    └── pipe-manufacturing-demo/   # bundled end-to-end demo
```

The demo's data-integrity rules use **generic placeholder tables** and cover, for example:

- **Inventory** — a confirmed receipt creates a movement; stock never goes negative; a shipment decreases stock; a cancellation restores stock.
- **Purchase** — a receipt updates the PO's received quantity; a cancelled PO blocks further receipts.
- **Production** — a completion creates a movement; good + defect equals total output; output stays within work-order quantity unless explicitly allowed.

For details, see the sibling docs above by name — this README intentionally does not duplicate them.

---

## 13. License & Contributing

> **DRAFT — to be finalized during implementation.**

- **License:** _TBD_ (intended to be a permissive open-source license; Codex will confirm and add `LICENSE`).
- **Contributing:** _TBD_ — contribution guidelines, issue templates, and a code of conduct will be added alongside the first release. For now, see `SPEC.md`, `CONSTRAINTS.md`, and `ACCEPTANCE_CRITERIA.md` to understand scope before proposing changes.
