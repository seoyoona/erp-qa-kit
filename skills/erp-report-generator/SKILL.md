# ERP Report Generator Skill

## Purpose

Propose and render human-readable QA report structure from validated local
artifacts.

## Inputs

- `qa-context/project_manifest.yaml`.
- `qa-context/entity_map.yaml`.
- `qa-context/flow_map.yaml`.
- `qa-context/rules/*.yaml`.
- `qa-context/generated/sql/generation_status.yaml`.

## Outputs

- Markdown QA report under `qa-context/reports/`.

## Steps

1. Summarize entities and flows by module.
2. Summarize rules by severity and verification type.
3. Summarize SQL generation status.
4. List every item that needs human confirmation.
5. State that humans make release decisions.

## Guardrails

- Do not issue release go/no-go decisions.
- Do not call an LLM or network service at runtime.
- Do not mutate input YAML while rendering reports.

## Human-Approval Points

- Humans interpret severity and release impact.
- Humans confirm low/medium-confidence report items.

