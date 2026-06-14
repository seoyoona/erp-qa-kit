# ERP Fix Handoff Skill

## Purpose

Convert QA findings and PM feedback into AI-readable handoff documents for a
separate coding agent working in the target ERP codebase.

## Inputs

- `qa-context/reports/`.
- `qa-context/rules/*.yaml`.
- `qa-context/entity_map.yaml`.
- `qa-context/flow_map.yaml`.
- `qa-context/feedback/feedback_items.yaml`.
- `qa-context/feedback/PM_FEEDBACK_TEMPLATE.md`.

## Outputs

- `qa-context/handoff/fix_handoff.md`.
- `qa-context/handoff/codex_fix_prompt.md`.
- Feedback templates if missing.

## Steps

1. Read structured feedback and related rules/flows.
2. Summarize expected behavior, actual behavior, reproduction steps, and evidence.
3. Point to likely affected modules or code paths.
4. Include related SQL assertions and validation-after-fix instructions.
5. Produce a ready-to-paste prompt for a downstream coding agent.

## Guardrails

- Do not modify target ERP source code.
- Do not claim a fix has been applied.
- Do not make release decisions.
- Write only under `qa-context/`.

## Human-Approval Points

- Humans review feedback accuracy and handoff instructions.
- Humans run the downstream coding agent and approve final fixes.

