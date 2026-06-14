# ERP QA Kit — Document Index (Read This First)

This repository is a **specification package** for Codex to implement the **first working
local release** of **ERP QA Kit** — an open-source, local-file-based, AI-assisted ERP
data-integrity QA framework.

These documents are the **single source of truth**. Implement exactly what they describe.
**Do not invent requirements, features, dependencies, integrations, table names, or links
beyond what these documents state.** When something is ambiguous, prefer the narrowest
interpretation that satisfies `ACCEPTANCE_CRITERIA.md` without violating `CONSTRAINTS.md`,
and record the assumption rather than expanding scope.

---

## Source-of-Truth Documents

| # | Document | Status | What it is |
|---|----------|--------|------------|
| 1 | [`SPEC.md`](./SPEC.md) | **Binding** | What to build: positioning, the 6-command pipeline, `qa-context/` layout, all YAML schemas, rule system, SQL safety model, feedback-to-fix handoff, the six `SKILL.md` specs, demo, repo tree, glossary. |
| 2 | [`CONSTRAINTS.md`](./CONSTRAINTS.md) | **Binding — hard limits** | What you must never do: human-in-the-loop gates, no-auto-modify of target code, local/offline only, no DB execution, the SQL deny-list, scope IN/OUT, provenance, determinism. Overrides convenience. |
| 3 | [`ACCEPTANCE_CRITERIA.md`](./ACCEPTANCE_CRITERIA.md) | **Binding — definition of done** | The testable checklist. The release is complete **only** when every criterion (sections A–L) passes. |
| 4 | [`ARCHITECTURE.md`](./ARCHITECTURE.md) | **Binding** | How to structure the code: module map (`cli`/`core`/`adapters`/`generators`/`reporters`), domain model, subsystems, file contracts, rule IR and exporter extension points. |
| 5 | [`ROADMAP.md`](./ROADMAP.md) | **Phase 1 binding; Phases 2–6 future** | Phase 1 = the first working release (build now). Phases 2–6 = future direction only; **do not implement**. Includes a suggested build order. |
| 6 | [`README_DRAFT.md`](./README_DRAFT.md) | **Binding (as the user guide to deliver)** | Draft README / usage guide. Finalize it as the shipped `README.md` so it matches the implemented CLI. |
| 7 | [`docs/integrations.md`](./docs/integrations.md) | **Reference — future targets, do not implement** | The authoritative, self-contained list of future integration tools with their **exact** official website and GitHub/doc links. Use these links verbatim. **Do not search the web or substitute other tools.** None are implemented in the first release. |

---

## Reading Order for Codex

1. **`INDEX.md`** (this file) — orientation and the rules of engagement.
2. **`SPEC.md`** — understand *what* to build end-to-end.
3. **`CONSTRAINTS.md`** — absorb the hard limits *before* writing code; they override everything.
4. **`ARCHITECTURE.md`** — learn *how* to lay out modules and data flow.
5. **`ROADMAP.md` (Phase 1 only)** — confirm scope and use the suggested build order.
6. **`ACCEPTANCE_CRITERIA.md`** — treat as the running checklist; build toward it and self-verify against it.
7. **`docs/integrations.md`** — read only to design the rule IR's exporter extension points; **implement none** of these integrations now.
8. **`README_DRAFT.md`** — keep it accurate to the real CLI; ship it as `README.md`.

---

## Binding vs. Future Roadmap

- **Binding now (must implement):** `SPEC.md`, `CONSTRAINTS.md`, `ACCEPTANCE_CRITERIA.md`,
  `ARCHITECTURE.md`, **Phase 1 of `ROADMAP.md`**, and the deliverable user guide
  (`README_DRAFT.md` → `README.md`).
- **Future roadmap (do NOT implement now):** `ROADMAP.md` Phases 2–6 and everything in
  `docs/integrations.md`. These exist so the architecture stays extensible — design for
  them, but build none of them in the first release.

If a "binding" and a "future" instruction ever appear to conflict, the **binding** documents win
and the future item stays unbuilt.

---

## Key Pointers

- **Definition of done → [`ACCEPTANCE_CRITERIA.md`](./ACCEPTANCE_CRITERIA.md).** The first
  working release is finished when the full pipeline runs end-to-end on
  `examples/pipe-manufacturing-demo/` (`init → intake → validate → generate-sql → report → handoff`)
  and every criterion in sections A–L passes.
- **Hard limits → [`CONSTRAINTS.md`](./CONSTRAINTS.md).** Local/offline, SELECT-only SQL with no
  DB execution, never modify target ERP code, human approval for business meaning/severity/release,
  provenance (`source` / `confidence` / `needs_human_confirmation`) on every inferred item.
- **Future integration targets & exact links → [`docs/integrations.md`](./docs/integrations.md).**
  Use the links there verbatim; do not invent alternatives or implement any integration.

---

## Scope Guardrail (restate)

> Implement the **first working local release** described by the binding documents — a usable,
> end-to-end toolkit on the bundled demo, not a partial prototype. **Do not add requirements,
> tools, dependencies, links, or features that these documents do not specify.** Anything not
> in scope here belongs to a future phase and must remain unbuilt.
