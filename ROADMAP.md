# ERP QA Kit — ROADMAP

> **Source of truth for phasing.** This document is read by an AI coding agent (Codex). It defines what to build **now** (Phase 1) and what is **explicitly deferred** (Phase 2+). For detailed behavior, contracts, and gates, see the sibling docs and do not duplicate them here:
> - `SPEC.md` — command/format/behavior specification
> - `CONSTRAINTS.md` — hard rules and guardrails
> - `ACCEPTANCE_CRITERIA.md` — Phase-1 exit gate
> - `ARCHITECTURE.md` — module/layer design
> - `docs/integrations.md` — future exporter/integration targets

**Product in one line:** ERP QA Kit is a local-file-based, AI-assisted ERP data-integrity QA framework. It runs a deterministic pipeline `init → intake → validate → generate-sql → report → handoff` via the CLI `erpqa`, where each command takes a `<project_path>`. First pilot target: a pipe-manufacturing ERP (~7 modules, ~140 pages).

---

## 1. Roadmap Principles

These invariants hold in **every** phase. Future work attaches to Phase 1 without violating them.

| # | Principle | What it means in practice |
|---|-----------|---------------------------|
| P1 | **PROPOSE / VERIFY / APPROVE invariant** | LLMs **propose** (drafts, candidate rules, mappings). Deterministic code **verifies** (schema validation, SELECT-only checks). Humans **approve** business meaning, severity, release, and final fixes. This separation is preserved across all phases. |
| P2 | **Deterministic + offline verification path** | Every verification step (YAML validation, SQL safety, report assertions) is deterministic and runs fully offline against local files. No network or live DB is required to verify a project. |
| P3 | **No auto-modification of target code** | The toolkit never edits, patches, or deploys the target ERP application code. Output is always advisory artifacts (reports, SQL, handoff notes) for humans to act on. |
| P4 | **Stable rule IR** | The internal rule intermediate representation (rule YAML schema) is designed now to remain **stable** so future exporters (SQL packs, Great Expectations, SodaCL, dbt, Schemathesis, Playwright, GraphWalker, AltWalker) attach later **without reworking** the rule format. |
| P5 | **Local-file-first** | State lives in the project folder. Each command is idempotent over `<project_path>` and reads/writes plain files (YAML, Markdown). |

---

## 2. Phase 1 — First Working Release (THE FOCUS)

### (a) Goal Statement

> **Phase 1 is usable end-to-end on the bundled pipe-manufacturing demo via `init → intake → validate → generate-sql → report → handoff`.** It is a complete first release, **not** a tiny partial prototype. A user can run all six commands in sequence against the demo project and obtain valid YAML artifacts, validated rules, SELECT-only SQL assertions, a Markdown report, and a feedback-to-fix handoff.

### (b) INCLUDED in Phase 1 — Build Now (checklist)

- [ ] Local Python CLI (`erpqa`), each subcommand takes `<project_path>`
- [ ] `qa-context` initialization (`init`)
- [ ] Project folder intake / source inventory (`intake`)
- [ ] `source_inventory.md` generation
- [ ] YAML formats + validation
- [ ] `project_manifest.yaml`
- [ ] `entity_map.yaml`
- [ ] `flow_map.yaml`
- [ ] Rule YAML files (internal rule IR)
- [ ] SELECT-only SQL safety checker
- [ ] `DB_ASSERTION` rule YAML → SQL assertion generation (`generate-sql`)
- [ ] Markdown report generation (`report`)
- [ ] Feedback-to-fix handoff generation (`handoff`)
- [ ] Pipe-manufacturing demo project (bundled, runnable end-to-end)
- [ ] Basic tests
- [ ] README usage guide
- [ ] Six `SKILL.md` spec files:
  - [ ] `skills/erp-intake`
  - [ ] `skills/erp-domain-modeler`
  - [ ] `skills/erp-rule-generator`
  - [ ] `skills/erp-test-generator`
  - [ ] `skills/erp-report-generator`
  - [ ] `skills/erp-fix-handoff`
- [ ] `docs/integrations.md` (documents future exporters; does **not** implement them)

### (c) EXCLUDED from Phase 1 — NOT in Phase 1

The following are **NOT in Phase 1**. Do **not** build them now:

- **NOT in Phase 1:** dashboard
- **NOT in Phase 1:** Playwright implementation
- **NOT in Phase 1:** API test generation
- **NOT in Phase 1:** real DB connection or SQL execution against a DB
- **NOT in Phase 1:** production DB access
- **NOT in Phase 1:** auto page crawler
- **NOT in Phase 1:** SaaS / multi-tenant architecture
- **NOT in Phase 1:** GraphWalker / model-based testing implementation
- **NOT in Phase 1:** GitHub marketplace / action
- **NOT in Phase 1:** complex plugin system
- **NOT in Phase 1:** direct integration with heavy third-party QA engines
- **NOT in Phase 1:** automatic modification of target ERP application code

### (d) Phase 1 Exit Criteria

Phase 1 is **done** only when every item in **`ACCEPTANCE_CRITERIA.md`** passes. In summary, the gate requires: all six commands run successfully in sequence on the bundled pipe-manufacturing demo; all generated YAML validates against its schema; generated SQL passes the SELECT-only safety checker; the Markdown report renders; the handoff artifact is produced; basic tests pass; and the README walkthrough reproduces the full pipeline. **`ACCEPTANCE_CRITERIA.md` is authoritative** — this section is a pointer, not a substitute.

---

## 3. Phase 1 Work Breakdown (suggested sequencing for Codex)

Build in this order so work doesn't tangle. Each step lists its dependencies and what completing it unblocks. Steps marked **‖ parallelizable** can proceed concurrently once their dependencies are met. See `ARCHITECTURE.md` for module layout and `SPEC.md` for exact contracts.

| # | Step | Depends on | Unblocks | Parallel? |
|---|------|-----------|----------|-----------|
| 1 | **Scaffolding & core schemas** — CLI skeleton (`erpqa` + 6 subcommands taking `<project_path>`), `qa-context`/`init`, and the YAML schemas for `project_manifest`, `entity_map`, `flow_map`, and the **rule IR** | — | Everything | No (foundational) |
| 2 | **Intake / adapters** — project folder scan, source inventory, `source_inventory.md` generation | 1 | Validation, demo, intake skill | No |
| 3 | **Validation** — deterministic YAML format validation for manifest, entity_map, flow_map, and rule files | 1 | `generate-sql`, report, handoff | No |
| 4 | **SQL safety checker** — SELECT-only safety checker (reject DML/DDL/multi-statement/etc.) | 1 | `generate-sql` | ‖ (parallel with 3) |
| 5 | **generate-sql** — `DB_ASSERTION` rule YAML → SQL assertion generation, gated by the SELECT-only checker | 3, 4 | Report (assertion results), handoff | No |
| 6 | **Reporters** — Markdown report generation from validated artifacts + generated SQL | 3, 5 | Handoff, exit gate | No |
| 7 | **Handoff** — feedback-to-fix handoff generation (advisory, never edits target code) | 6 | Exit gate | No |
| 8 | **Demo data** — bundled pipe-manufacturing demo project (sources, manifest, maps, rules) | 1–7 schemas | End-to-end run, tests | ‖ (can draft alongside 2–7 once schemas from 1 freeze) |
| 9 | **Tests** — basic tests covering CLI, validation, SQL safety, generate-sql, report, handoff on the demo | 1–8 | Exit gate | Partly ‖ (per-module tests as each lands) |
| 10 | **Docs & skills** — README usage guide, six `SKILL.md` files, `docs/integrations.md` | 1–8 stable contracts | Exit gate | ‖ (each SKILL.md and docs file independent) |

**Notes for Codex:**
- Freeze the **rule IR schema (step 1)** before writing rules, exporters docs, or generate-sql — changing it later forces rework (see P4).
- Steps 4, 8, 9 (per-module), and 10 are the main parallelization opportunities once step 1 lands.
- Never let `generate-sql` (step 5) emit SQL that hasn't passed step 4.

---

## 4. Phase 2 — Rule Exporters (future) — **NOT NOW**

Export the **stable rule IR** to external formats, each as an exporter behind a single stable interface so the IR never has to change per target.

| Exporter | Target | Source rule kind |
|----------|--------|------------------|
| Raw SQL pack | SQL assertion files | `DB_ASSERTION` |
| Great Expectations / GX Core | Expectations | `DB_ASSERTION` |
| SodaCL (Soda Core) | YAML/CLI checks | `DB_ASSERTION` |
| dbt tests (dbt Core) | not_null / unique / accepted_values / relationships / model tests | `DB_ASSERTION` |

- All targets documented in **`docs/integrations.md`**; none implemented in Phase 1.
- Each exporter is a thin adapter over the rule IR; the IR is the contract (P4).
- **Status: NOT implemented yet.**

---

## 5. Phase 3 — API Testing (future) — **NOT NOW**

| Item | Direction |
|------|-----------|
| `API_ASSERTION` rule kind maturation | New rule IR kind, designed to coexist with `DB_ASSERTION` |
| Schemathesis configs | Export `API_ASSERTION` → OpenAPI/GraphQL property-based test configs |
| Keploy | API record / replay / mocks / regression |

- Documented in **`docs/integrations.md`**.
- **Status: NOT implemented yet.**

---

## 6. Phase 4 — UI / Flow Testing (future) — **NOT NOW**

| Item | Source artifact |
|------|-----------------|
| Playwright test **skeletons** | Approved `flow_map.yaml` + rules |

- Generates skeletons only; no live browser automation engine bundled in this toolkit's core.
- Depends on a human-**approved** `flow_map` (P1).
- Documented in **`docs/integrations.md`**.
- **Status: NOT implemented yet.**

---

## 7. Phase 5 — Model-Based Testing (future) — **NOT NOW**

| Item | Source artifact | Notes |
|------|-----------------|-------|
| GraphWalker graph models | `flow_map.yaml` (ERP state transitions) | Model-based testing |
| AltWalker models + Python skeletons | `flow_map.yaml` | Python-friendly model-based execution |

- Documented in **`docs/integrations.md`**.
- **Status: NOT implemented yet.**

---

## 8. Phase 6 — Optional Surfaces (future, lower priority) — **NOT NOW**

| Surface | One-line rationale for deferral |
|---------|---------------------------------|
| Dashboard | Markdown reports satisfy Phase-1 consumption; UI is a presentation layer that can wait. |
| Real (safe, read-only) DB execution harness | Phase 1 generates SQL but verifies offline; live execution adds infra/security scope not needed to prove the pipeline. |
| GitHub action / marketplace | CI distribution is packaging, valuable only after the core is stable. |
| Plugin system | A complex extension surface risks over-engineering before exporters prove the IR boundary. |
| SaaS / multi-tenant | Local-file-first (P5) is the design center; multi-tenant is a different product shape. |

- **Status: NOT implemented yet.**

---

## 9. Cross-Phase Dependencies & Sequencing

| Future phase / item | Depends on Phase-1 artifact | Why |
|---------------------|-----------------------------|-----|
| Phase 2 — all exporters | **Stable rule IR** (rule YAML schema) | Exporters are adapters over the IR; the IR must not churn (P4). |
| Phase 2 — Raw SQL / GX / SodaCL / dbt | `DB_ASSERTION` rules + SELECT-only checker | Reuse the same assertion semantics validated in Phase 1. |
| Phase 3 — Schemathesis / Keploy | `API_ASSERTION` kind (extends rule IR) | New rule kind slots into the existing IR shape. |
| Phase 4 — Playwright skeletons | **Approved** `flow_map.yaml` + rules | Skeletons are generated from human-approved flows (P1). |
| Phase 5 — GraphWalker / AltWalker | **Approved** `flow_map.yaml` | Model-based tests are derived from the flow graph. |
| Phase 6 — DB execution harness | `generate-sql` output + SELECT-only checker | Safe read-only execution reuses Phase-1 SQL safety guarantees. |
| Phase 6 — dashboard / action / plugin / SaaS | Phase-1 report + artifact contracts | Presentation/distribution layers wrap stable Phase-1 outputs. |

**Sequencing rule:** nothing in Phases 2–6 starts until the Phase-1 exit gate (`ACCEPTANCE_CRITERIA.md`) passes and the rule IR + `flow_map` schemas are frozen.

---

## 10. Out-of-Scope Tracker (consolidated)

Every deferred item, the phase it is parked in, and its status. All are **not implemented yet**.

| Deferred item | Parked in phase | Status |
|---------------|-----------------|--------|
| Raw SQL assertion pack exporter | Phase 2 | Not implemented yet |
| Great Expectations / GX Core exporter | Phase 2 | Not implemented yet |
| SodaCL (Soda Core) exporter | Phase 2 | Not implemented yet |
| dbt tests exporter | Phase 2 | Not implemented yet |
| API test generation (`API_ASSERTION`) | Phase 3 | Not implemented yet |
| Schemathesis configs | Phase 3 | Not implemented yet |
| Keploy record/replay/mocks/regression | Phase 3 | Not implemented yet |
| Playwright implementation / UI E2E skeletons | Phase 4 | Not implemented yet |
| GraphWalker model-based testing | Phase 5 | Not implemented yet |
| AltWalker model-based execution | Phase 5 | Not implemented yet |
| Dashboard | Phase 6 | Not implemented yet |
| Real / read-only DB connection & SQL execution | Phase 6 | Not implemented yet |
| Production DB access | Phase 6 | Not implemented yet |
| Auto page crawler | Phase 6 | Not implemented yet |
| GitHub marketplace / action | Phase 6 | Not implemented yet |
| Complex plugin system | Phase 6 | Not implemented yet |
| SaaS / multi-tenant architecture | Phase 6 | Not implemented yet |
| Direct integration with heavy third-party QA engines | Phase 2–5 (as exporters) | Not implemented yet |
| Automatic modification of target ERP application code | Never (violates P3) | Never — prohibited by invariant |

---

*Phase 1 is the contract. Phases 2–6 describe direction only and must not be implemented until the Phase-1 gate passes. The PROPOSE / VERIFY / APPROVE invariant and the no-auto-modify rule hold in every phase.*
