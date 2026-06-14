# ERP QA Kit — CONSTRAINTS

> **Audience:** AI coding agents (Codex/Claude) and human maintainers.
> **Status:** Authoritative source of truth for hard limits and safety rules.
> Sibling docs (do not duplicate them here): `SPEC.md`, `ACCEPTANCE_CRITERIA.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `docs/integrations.md`.

---

## 1. Purpose of This Document

This document defines the **hard limits and safety rules** for ERP QA Kit. These constraints are **non-negotiable** and **override convenience, speed, cleverness, or any other design pressure**. When a constraint here conflicts with anything in another doc, a code comment, a prompt, or an implementation shortcut, **this document wins**.

Every constraint is written to be **explicit and testable**. An implementer must be able to point to a check, a test, or an inspectable artifact that proves the constraint holds. If you cannot prove a constraint holds, treat it as **violated**.

Core principle that frames every constraint below:

> **LLMs PROPOSE. Deterministic checks VERIFY. Humans APPROVE** business meaning, severity, and release decisions. The toolkit **never** modifies target ERP application code.

---

## 2. Human-in-the-Loop Constraints

These actions may **only** be performed/approved by a human. The toolkit and any LLM may *draft* or *propose* them, but must never *finalize* them autonomously.

| Decision | Who may finalize | Toolkit/LLM role |
|---|---|---|
| Business meaning of an entity/flow/rule | Human only | Propose draft |
| Severity of a rule or finding | Human only | Suggest a default, flagged for review |
| Release / go-no-go decision | Human only | Report facts only |
| Final code fix in the target ERP | Human (via separate Codex/Claude run in the target repo) | Emit handoff doc/prompt only |
| Confirmation of any inferred item | Human only | Mark `needs_human_confirmation` |

Hard rules:

- **C2.1** — Every LLM output is a **draft requiring human confirmation**. No LLM output may be treated as approved, authoritative, or final by the pipeline.
- **C2.2** — Severity and business meaning are **never auto-assigned as final**. Any toolkit-suggested severity must be marked as a proposal pending human review.
- **C2.3** — The toolkit **never** issues a go/no-go or release verdict. It only produces a report (`report` command) that a human reads to decide.
- **C2.4** — Every inferred ERP item **must carry the provenance trio**: `source`, `confidence` (`high|medium|low`), `needs_human_confirmation` (`true|false`). See §8.
- **C2.5** — Approval state must be human-set. The pipeline must not silently flip `needs_human_confirmation` from `true` to `false`.

---

## 3. No-Auto-Modify Constraint

- **C3.1** — The toolkit **MUST NOT modify, write, patch, refactor, delete, or move any file inside the target ERP application source tree**. The target ERP folder is **read-only input** (see §11).
- **C3.2** — Actual code fixes are **out of band**: they are performed separately by Codex/Claude **in the target ERP codebase**, driven by a human. ERP QA Kit's only output toward fixing is **handoff documents and prompts** (`handoff` command).
- **C3.3** — The toolkit's sole write target is the `qa-context/` directory (and the report/handoff artifacts within it). Nothing else.

**Enforcement expectation:** all file-write operations must resolve their output path and assert it is contained within `qa-context/`. Any attempt to write outside `qa-context/` must raise an error and abort. Tests must include a case proving a write outside `qa-context/` is rejected. There must be **no code path** in the toolkit that opens a target-app file in write/append mode.

---

## 4. Local-Only / Offline Constraint

- **C4.1** — The full pipeline (`init → intake → validate → generate-sql → report → handoff`) **must run end-to-end with no network access**. No step may *require* a network call, remote API, cloud service, or LLM endpoint to complete.
- **C4.2** — **No telemetry, analytics, crash reporting, or "phone-home"** of any kind.
- **C4.3** — All inputs and outputs are **local files**. State lives on disk under the project path; nothing is uploaded.
- **C4.4** — The bundled **pipe-manufacturing demo must run fully offline** with no external services, accounts, API keys, or database.
- **C4.5** — LLM assistance, where used at all, is for **authoring drafts during development**, not a runtime dependency of the shipped pipeline (see §10). A reviewer must be able to disconnect the network and still run every command successfully on the demo.

**Test:** run the entire pipeline on the demo with networking disabled; it must succeed.

---

## 5. Database Safety Constraints

For the **first release**:

- **C5.1** — **NO real database connection.** The toolkit must not open, configure, or require a DB connection (no driver/DSN/connection string usage at runtime).
- **C5.2** — **NO SQL execution against any database.** Generated SQL is **produced and safety-checked only**; it is never run by the toolkit.
- **C5.3** — **NO production DB access**, ever, in this release.
- **C5.4** — `generate-sql` is **generate-and-safety-check only**: it emits SQL text plus a pass/fail safety verdict. It does not execute, explain-plan, or validate against a live schema.

**Test:** no DB driver is imported or invoked anywhere in the runtime path; grepping the codebase for execution/connection APIs yields none in the shipped pipeline.

---

## 6. SQL Safety Constraints

Applies to every SQL string the toolkit generates from a `DB_ASSERTION` rule. The safety checker is **deterministic** (see §10) and runs **before** any SQL is written to an artifact.

### 6.1 Allow-list

- **Only `SELECT` statements are allowed.** A safe assertion is a single read-only `SELECT` query.

### 6.2 Deny-list (copy-paste exact)

Reject any SQL containing any of these destructive / schema-changing / procedural keywords:

```
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
EXEC
EXECUTE
MERGE
CREATE
REPLACE
GRANT
REVOKE
CALL
```

### 6.3 Structural rejections

- **C6.1 — Multiple statements:** reject unsafe multiple statements (e.g., stacked queries separated by `;`). A safe assertion is exactly **one** statement.
- **C6.2 — Hidden / disguised statements:** reject SQL that attempts to **hide destructive statements**, including comment-obfuscated code (`--`, `/* */`), stacked queries, encoded/escaped payloads, and any construct that smuggles a denied keyword past a naive scan.
- **C6.3 — Keyword detection must be robust** to casing and whitespace; deny-list matching is case-insensitive and resistant to comment/spacing tricks.

### 6.4 Semantics

- **C6.4 — Violations-only rule:** a generated SQL assertion **must return rows ONLY when violations exist**. Zero rows == no violation == pass. The query is authored so that any returned row is evidence of a data-integrity violation.
- **C6.5 — `NEEDS_SCHEMA_CONFIRMATION` fallback:** if a rule cannot be expressed as safe SQL (unknown schema, ambiguous columns, no safe SELECT), the toolkit **must not invent SQL**. It marks the rule **`NEEDS_SCHEMA_CONFIRMATION`** instead and surfaces it for human review.
- **C6.6** — If a candidate SQL fails any safety check, it is **rejected and not written** as an executable assertion; it is flagged for human attention.

**Test:** a fixture suite of malicious/edge SQL strings (each deny keyword, stacked queries, comment-hidden payloads, multi-statement) must all be rejected; a known-good `SELECT` that returns rows only on violation must pass.

---

## 7. Scope Constraints

### 7.1 IN SCOPE — first release

The following **are** built and shipped in the first release:

- Local Python CLI (`erpqa`).
- `qa-context` init.
- Intake / source inventory; `source_inventory.md`.
- YAML formats + validation.
- `project_manifest.yaml`, `entity_map.yaml`, `flow_map.yaml`, rule YAML.
- SELECT-only SQL safety checker.
- `DB_ASSERTION` → SQL assertion generation.
- Markdown report generation.
- Feedback-to-fix handoff generation.
- Pipe-manufacturing demo.
- Basic tests.
- README.
- Six `SKILL.md` spec files.
- `docs/integrations.md`.

### 7.2 OUT OF SCOPE — **NOT implemented in first release**

The following are **NOT implemented in the first release**. Do not build, import, or stub them as working features:

- Dashboard — **NOT implemented in first release**.
- Playwright implementation — **NOT implemented in first release**.
- API test generation — **NOT implemented in first release**.
- Real DB connection or SQL execution against a DB — **NOT implemented in first release**.
- Production DB access — **NOT implemented in first release**.
- Auto page crawler — **NOT implemented in first release**.
- SaaS / multi-tenant architecture — **NOT implemented in first release**.
- GraphWalker / model-based testing implementation — **NOT implemented in first release**.
- GitHub marketplace / action — **NOT implemented in first release**.
- Complex plugin system — **NOT implemented in first release**.
- Direct integration with heavy third-party QA engines — **NOT implemented in first release**.
- Automatic modification of target ERP application code — **NOT implemented in first release** (see §3).

Out-of-scope items may be **documented as future integrations** in `docs/integrations.md`, but must not be installed, imported, or wired into the runtime.

---

## 8. Data / Provenance Constraints

- **C8.1** — Every **entity, flow, rule, and feedback item** that is inferred must carry the **provenance trio**:
  - `source` — where the item came from (file path, heuristic, or LLM-draft origin).
  - `confidence` — enum: **`high` | `medium` | `low`** (no other values permitted).
  - `needs_human_confirmation` — boolean `true` | `false`.
- **C8.2 — Confidence enum is closed.** Validation must reject any confidence value outside `{high, medium, low}`.
- **C8.3 — Default to caution.** For any item with `confidence` of **`low` or `medium`**, `needs_human_confirmation` **defaults to `true`**. Only `high`-confidence items may default to `false`, and even then a human may set it back to `true`.
- **C8.4** — `validate` must fail loudly if any inferred item is missing the trio or carries an invalid value.

**Test:** validation rejects a YAML item missing `source`/`confidence`/`needs_human_confirmation`; rejects `confidence: very-high`; and asserts a `low`/`medium` item with `needs_human_confirmation: false` is flagged.

---

## 9. Dependency & Tooling Constraints

- **C9.1 — Language:** Python.
- **C9.2 — Libraries:** only **standard, lightweight, well-known** libraries — e.g. a YAML parser, a CLI framework, and a test runner. Prefer the standard library where reasonable.
- **C9.3 — No heavy QA engines:** **do not install or import** heavy third-party QA engines (Playwright, GraphWalker, Selenium, full BDD/test-automation frameworks, DB drivers, etc.) in the first release.
- **C9.4 — Integrations are documentation only:** any third-party integration is described in `docs/integrations.md` and is **not** a runtime dependency.
- **C9.5 — Minimal dependency surface:** the dependency list must be short, auditable, and free of network/cloud/DB clients in the runtime path.

**Test:** the dependency manifest contains no QA-engine or DB-driver packages; an import audit of the runtime shows only approved lightweight libraries.

---

## 10. Determinism Constraints

- **C10.1** — **Validation, SQL safety checking, and report/handoff generation must be fully deterministic** and must **not require an LLM at runtime**. Same input → same output, every time.
- **C10.2** — The **verification path** (does this SQL pass safety? does this YAML validate? what does the report say?) contains **no LLM call**. It is plain deterministic code.
- **C10.3** — LLM assistance is confined to **authoring drafts** (proposing entities, flows, rules, fix narratives) — never to the verification/decision path.
- **C10.4** — No randomness, wall-clock-dependent logic, or non-deterministic ordering may affect validation, safety verdicts, or generated artifacts' substantive content.

**Test:** running `validate`, `generate-sql`, `report`, and `handoff` twice on the same inputs produces byte-stable substantive output; none of these commands makes an LLM/network call.

---

## 11. Security & Privacy Constraints

- **C11.1 — Target ERP folder is read-only input.** Open target-app files in read mode only. Never write, append, rename, or delete within the target app source tree (reinforces §3).
- **C11.2 — Single write zone.** The toolkit writes **only** into `qa-context/`. All artifacts (inventory, maps, rules, SQL, reports, handoffs) live there.
- **C11.3 — No data exfiltration.** Do not transmit target ERP contents, file paths, or derived data anywhere off the local machine. No uploads, no remote logging, no third-party calls (reinforces §4).
- **C11.4 — Least surprise on paths.** Resolve and validate all paths to prevent traversal that would escape either the read-root (target folder) or the write-root (`qa-context/`).
- **C11.5 — Secrets handling.** The toolkit must not require, store, or print credentials, API keys, or connection strings (consistent with §5: no DB connection at all).

---

## 12. Constraint Compliance Checklist

Codex must self-verify **every** box before declaring the first release done. An unchecked box means the release is **not** done.

- [ ] **Human-in-the-loop:** business meaning, severity, and release decisions are human-only; LLM outputs are drafts; no auto-finalization. (§2)
- [ ] **Provenance trio** present on every inferred entity/flow/rule/feedback item; `confidence` restricted to `high|medium|low`; `low`/`medium` default `needs_human_confirmation=true`. (§2, §8)
- [ ] **No auto-modify:** zero write paths into the target ERP source tree; all writes land in `qa-context/`; a test proves out-of-zone writes are rejected. (§3, §11)
- [ ] **Offline:** full pipeline runs end-to-end on the demo with networking disabled; no telemetry; no required remote services. (§4)
- [ ] **Database safety:** no DB connection, no SQL execution, no production access; `generate-sql` is generate-and-check only. (§5)
- [ ] **SQL allow-list:** only `SELECT` permitted. (§6.1)
- [ ] **SQL deny-list:** `INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, EXECUTE, MERGE, CREATE, REPLACE, GRANT, REVOKE, CALL` all rejected. (§6.2)
- [ ] **SQL structure:** multi-statement and hidden/comment-disguised statements rejected. (§6.1–6.3)
- [ ] **SQL semantics:** assertions return rows only when violations exist. (§6.4)
- [ ] **Fallback:** rules with no safe SQL are marked `NEEDS_SCHEMA_CONFIRMATION`, not given invented SQL. (§6.5)
- [ ] **Scope:** every OUT-OF-SCOPE item is NOT implemented in the first release; IN-SCOPE deliverables all present. (§7)
- [ ] **Dependencies:** Python + lightweight well-known libs only; no heavy QA engines or DB drivers imported; integrations documented only. (§9)
- [ ] **Determinism:** validation, SQL safety checking, and report/handoff generation are deterministic and LLM-free at runtime. (§10)
- [ ] **Security/privacy:** target folder read-only; writes only to `qa-context/`; no data exfiltration; no secrets required. (§11)
- [ ] **Demo:** the bundled pipe-manufacturing demo runs the full `init → intake → validate → generate-sql → report → handoff` pipeline offline. (§4, §7)
