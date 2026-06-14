# ERP Rule Generator Skill

## Purpose

Propose human-reviewable ERP data-integrity rules from approved or draft entity
and flow maps.

## Inputs

- `qa-context/entity_map.yaml`.
- `qa-context/flow_map.yaml`.
- Local business docs and screen specs.
- Optional reusable rule packs under `rule_packs/`.

## Outputs

- Draft `qa-context/rules/*.yaml` files using the rule IR.
- Provenance trio on every inferred rule.

## Steps

1. Identify data-integrity risks from cross-module flows.
2. Draft rules with stable `rule_id`, module, flow, severity proposal, and verification type.
3. Populate required entity and table references from the maps.
4. For `DB_ASSERTION`, include SQL only when a safe SELECT is evident.
5. Use `sql: null` when schema confirmation is needed.

## Guardrails

- Do not make severity final; it is a human decision.
- Do not invent table names or flows beyond local evidence.
- Do not implement API, UI, model-based, or third-party QA integrations.
- Do not execute SQL.

## Human-Approval Points

- Humans approve business meaning, severity, and release relevance.
- Humans confirm ambiguous schema before SQL is trusted.

