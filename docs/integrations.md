# ERP QA Kit — Integrations

> **Status banner:** NONE of the tools described in this document are implemented, installed, imported, executed, or required in the first working release of ERP QA Kit. This file documents *future integration targets* only.

---

## 1. Purpose & How to Read This File

This is the **authoritative, self-contained list of future integration targets** for ERP QA Kit.

ERP QA Kit is a local-file-based, AI-assisted ERP data-integrity QA framework. It models ERP entities and business flows, generates human-reviewable data-integrity rules, converts approved `DB_ASSERTION` rules into SELECT-only SQL assertions, generates Markdown reports, and produces AI-readable fix-handoff documents. Its core principle is: **LLMs propose, deterministic checks verify, humans approve.**

If you are an AI coding agent (e.g., Codex) reading this file, follow these rules:

- **Treat the links in this file as canonical.** Every tool below is listed with its exact official website and exact official GitHub/documentation URL. Use those URLs verbatim.
- **Do NOT search the web** for these tools, do NOT substitute alternative tools, do NOT invent unofficial repositories, and do NOT add extra links. If a tool is not in this document, it is not a sanctioned integration target.
- **Do NOT implement any integration** described here. Every entry is a forward-looking design note. The phrase "**NOT implemented in the first working release**" applies to all eight tools without exception.
- This document is **self-contained**: it tells you what each tool is, where it would attach in the ERP QA Kit architecture, why it is deliberately not built yet, and what a future exporter could look like. You should never need to look anything up elsewhere to understand the integration intent.

The eight future integration targets are:

1. Great Expectations / GX Core
2. Soda Core
3. dbt Core / dbt tests
4. Schemathesis
5. Keploy
6. Playwright
7. GraphWalker
8. AltWalker

---

## 2. Integration Philosophy

ERP QA Kit's design follows one principle end-to-end: **LLMs propose, deterministic checks verify, humans approve.** LLMs help model entities and flows and propose candidate rules; deterministic, reviewable artifacts (SQL assertions, structured rules) do the actual verification; and a human approves rules before they are ever executed.

For integrations, this translates into a deliberately conservative stance for the first working release:

- The first release **ships a stable internal rule IR** (the rule / entity_map / flow_map YAML contract described in Section 3) plus **exporter EXTENSION POINTS** in the architecture.
- The first release **installs and integrates none of the engines** in this document. There is no runtime dependency, no network call, no import, and no required external process for any of the eight tools.
- Future integrations are intended to be **thin exporters**: small, single-direction translators that read the stable internal IR and emit a configuration/test artifact for a target tool. They are *not* heavy runtime couplings, plugins, or embedded engines.
- This keeps ERP QA Kit's core deterministic and self-hosted, and keeps the third-party engines as **optional, downstream consumers** of approved artifacts — never as a dependency the core needs in order to function.

In short: build a durable contract now, write thin exporters later, couple to nothing today.

---

## 3. The Internal Rule IR as the Integration Contract

The **integration contract** is the ERP QA Kit internal rule IR — the rule, entity, and flow YAML produced and approved inside ERP QA Kit. Future exporters read this IR; they do not reach into ERP QA Kit internals. As long as the IR is stable, exporters can be added, removed, or revised without touching the core.

The IR consists of three artifact families:

- **Rule YAML** — each rule carries:
  - `verification_type` ∈ `{DB_ASSERTION, API_ASSERTION, UI_ASSERTION, MANUAL}`
  - `severity` ∈ `{BLOCKER, MAJOR, MINOR}`
  - `required_entities`, `required_tables`
  - `sql`, `expected_result`
  - `provenance` (`source`, `confidence`, `needs_human_confirmation`)
- **`entity_map.yaml`** — models entities ↔ physical tables/columns.
- **`flow_map.yaml`** — models business flows: `steps`, `trigger_screen`, `user_action`, `related_entities`, `affected_tables`, `status_transitions`, `downstream_side_effects`.

How the IR maps to integration surfaces:

- **DB-quality tools** attach at `DB_ASSERTION` rules and `entity_map.yaml`.
- **API tools** attach at `API_ASSERTION` rules and API specs.
- **UI and model-based tools** attach at `flow_map.yaml` (`UI_ASSERTION` rules and `status_transitions`).

The IR is designed to be exportable later to exactly **eight export targets** (none implemented in the first release):

1. **Raw SQL assertions** — a SELECT-only SQL pack.
2. **Great Expectations** expectations.
3. **SodaCL** checks.
4. **dbt tests.**
5. **Schemathesis** configs.
6. **Playwright** test skeletons.
7. **GraphWalker** graph models.
8. **AltWalker** models.

---

## 4. Integration Targets

Each subsection below documents one future integration target. **Every URL is reproduced exactly as sanctioned. None of these are implemented in the first working release.**

### 4.1 Great Expectations / GX Core

| Field | Value |
|---|---|
| Official website | https://greatexpectations.io/gx-core/ |
| Official GitHub | https://github.com/great-expectations/great_expectations |
| Problem it solves | DB/data-quality validation: declaratively asserting expectations about data (nulls, ranges, uniqueness, referential expectations) and producing validation results. |
| Where it fits | Attaches at `DB_ASSERTION` rules and `entity_map.yaml`. The entity↔table/column mapping supplies the targets; the rule's `expected_result` informs the expectation. |
| Why NOT implemented in first release | The first release keeps DB verification deterministic and self-hosted via SELECT-only SQL assertions, with no external validation engine, dependency, or runtime coupling. |
| What a future exporter could look like | An exporter that reads approved `DB_ASSERTION` rules plus `entity_map.yaml` and emits a GX-compatible **expectation suite** targeting the mapped tables/columns. |

### 4.2 Soda Core

| Field | Value |
|---|---|
| Official website | https://www.soda.io/ |
| Official GitHub | https://github.com/sodadata/soda-core |
| Problem it solves | YAML/CLI-based data-quality checks (SodaCL) run against a database or warehouse. |
| Where it fits | Attaches at `DB_ASSERTION` rules and `entity_map.yaml`. |
| Why NOT implemented in first release | No external data-quality engine is bundled or required; DB verification ships only as SELECT-only SQL assertions in the first release. |
| What a future exporter could look like | An exporter that reads approved `DB_ASSERTION` rules and `entity_map.yaml` and emits **SodaCL checks** (a `checks.yml`-style file) over the mapped datasets. |

### 4.3 dbt Core / dbt tests

| Field | Value |
|---|---|
| Official website | https://www.getdbt.com/ |
| Official GitHub | https://github.com/dbt-labs/dbt-core |
| Problem it solves | SQL model tests and data tests: `not_null`, `unique`, `accepted_values`, relationship/referential-integrity tests, plus custom singular tests. |
| Where it fits | Attaches at `DB_ASSERTION` rules and `entity_map.yaml` (entity/table/column targets map naturally to dbt generic tests; complex rules map to singular tests). |
| Why NOT implemented in first release | ERP QA Kit does not assume or require a dbt project; the first release stays independent of any modeling/transformation framework. |
| What a future exporter could look like | An exporter that reads approved `DB_ASSERTION` rules and `entity_map.yaml` and emits **dbt generic tests** (in `schema.yml`) for standard constraints and **dbt singular tests** (SQL files) for rule-specific assertions. |

### 4.4 Schemathesis

| Field | Value |
|---|---|
| Official website | https://schemathesis.io/ |
| Official GitHub | https://github.com/schemathesis/schemathesis |
| Problem it solves | Property-based API testing driven by an OpenAPI/GraphQL schema, automatically generating and checking many request cases. |
| Where it fits | Attaches at `API_ASSERTION` rules and API specs. |
| Why NOT implemented in first release | The first release does not execute or generate live API tests; API-level verification is documented as a future capability only. |
| What a future exporter could look like | An exporter that reads `API_ASSERTION` rules alongside an API spec and emits **Schemathesis configs** / a test-invocation setup targeting the relevant endpoints. |

### 4.5 Keploy

| Field | Value |
|---|---|
| Official website | https://keploy.io/ |
| Official GitHub | https://github.com/keploy/keploy |
| Problem it solves | API traffic recording, replay, mock generation, and regression testing from captured real traffic. |
| Where it fits | Attaches at `API_ASSERTION` rules and API specs. |
| Why NOT implemented in first release | ERP QA Kit does not record or replay live ERP traffic in the first release; this is a documented future regression-testing avenue only. |
| What a future exporter/integration could look like | Documentation/tooling describing how **Keploy** could capture real ERP API flows and replay them as regression tests, with `API_ASSERTION` rules used to express expected outcomes. |

### 4.6 Playwright

| Field | Value |
|---|---|
| Official website | https://playwright.dev/ |
| Official GitHub | https://github.com/microsoft/playwright |
| Problem it solves | UI/end-to-end browser automation for validating user workflows. |
| Where it fits | Attaches at `flow_map.yaml` and `UI_ASSERTION` rules. `trigger_screen`, `user_action`, and `steps` describe the workflow to drive. |
| Why NOT implemented in first release | The first release produces approved entity maps, flow maps, and rules but does not generate or run UI tests; UI/E2E validation is a later phase. |
| What a future exporter could look like | An exporter that reads approved `flow_map.yaml` and `UI_ASSERTION` rule YAML and emits **Playwright test skeletons** scaffolding the navigation/actions per flow for a human to complete. |

### 4.7 GraphWalker

| Field | Value |
|---|---|
| Official website | https://graphwalker.github.io/ |
| Official GitHub organization | https://github.com/graphwalker |
| Problem it solves | Model-based testing: walking a graph model of states/transitions to generate test paths and measure coverage. |
| Where it fits | Attaches at `flow_map.yaml`, specifically `status_transitions` and `steps` (states and transitions of ERP business flows). |
| Why NOT implemented in first release | The first release models flows as data but does not generate or execute model-based test walks; this is a documented future capability. |
| What a future exporter could look like | An exporter that reads `flow_map.yaml` (states from `status_transitions`, edges from `steps`/`user_action`) and emits **GraphWalker-compatible graph models** for path generation and coverage. |

### 4.8 AltWalker

| Field | Value |
|---|---|
| Official documentation | https://altwalker.github.io/altwalker/ |
| Official GitHub | https://github.com/altwalker/altwalker |
| Problem it solves | Python-friendly model-based testing execution, running tests against graph models (works in the GraphWalker model ecosystem). |
| Where it fits | Attaches at `flow_map.yaml`, specifically `status_transitions` and `steps`. |
| Why NOT implemented in first release | As with GraphWalker, flows are modeled as data only in the first release; no model-based execution is built. |
| What a future exporter could look like | An exporter that reads `flow_map.yaml` and emits **AltWalker-compatible models** plus **Python test skeletons** for model-based execution. |

---

## 5. Mapping Table

| ERP QA Kit artifact / verification_type | Candidate future tool(s) | Export direction | Status |
|---|---|---|---|
| `DB_ASSERTION` / `entity_map.yaml` | Great Expectations, Soda Core, dbt Core | ERP QA Kit IR → GX expectation suite / SodaCL checks / dbt tests | Not implemented yet |
| `API_ASSERTION` / API specs | Schemathesis, Keploy | ERP QA Kit IR → Schemathesis configs / Keploy record-replay regression tests | Not implemented yet |
| `flow_map.yaml` / `UI_ASSERTION` | Playwright | ERP QA Kit IR → Playwright test skeletons | Not implemented yet |
| `flow_map.yaml` / `status_transitions` (state transitions) | GraphWalker, AltWalker | ERP QA Kit IR → GraphWalker graph models / AltWalker models + Python skeletons | Not implemented yet |
| All `DB_ASSERTION` rules | Raw SQL pack | ERP QA Kit IR → SELECT-only SQL assertion pack | Not implemented yet |

---

## 6. Non-Goals for the First Release

For the first working release, the following are explicit non-goals:

- **None of these tools are installed.** No package, binary, or service for Great Expectations, Soda Core, dbt Core, Schemathesis, Keploy, Playwright, GraphWalker, or AltWalker is added.
- **None are imported.** The core does not `import`/`require` any of these libraries.
- **None are executed.** ERP QA Kit does not run, shell out to, or orchestrate any of these engines.
- **None are required.** ERP QA Kit functions fully without any of them present.
- **No network or runtime dependency** on any of these tools — no API calls, no traffic capture, no remote model execution.
- **No exporters for these tools are built** in the first release; the export targets in Section 3 exist as a documented contract only.
- To restate plainly: every integration in this document is **not implemented yet**.

---

## 7. How to Add an Exporter Later

When an exporter is eventually built, it must be added through the **exporter extension point** described in `ARCHITECTURE.md`. Do not couple exporters into the core verification path and do not introduce a runtime dependency on the target engine.

Design-level expectations (see `ARCHITECTURE.md` for the authoritative description — referenced by name here, not duplicated):

- An exporter is a **thin, single-direction translator**: it reads the stable internal rule IR (rule / `entity_map.yaml` / `flow_map.yaml`) and emits a configuration/test artifact for one target tool.
- An exporter **consumes approved artifacts only** and produces output files; it does not execute the target engine and does not feed results back into the core.
- Adding an exporter must not change the IR contract in Section 3. If the IR must change, that is a contract revision handled separately from exporter work.

Refer to the exporter extension point in `ARCHITECTURE.md` for the concrete interface and registration details.
