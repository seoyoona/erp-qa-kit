# ERP Domain Modeler Skill

## Purpose

Propose ERP entities and business flows from local source evidence so humans can
review `entity_map.yaml` and `flow_map.yaml`.

## Inputs

- `qa-context/source_inventory.md`.
- Local DB schema, docs, API specs, screen specs, backend, and frontend files.
- Existing `qa-context/entity_map.yaml` and `qa-context/flow_map.yaml`, if present.

## Outputs

- Draft `qa-context/entity_map.yaml`.
- Draft `qa-context/flow_map.yaml`.
- Provenance trio on every inferred entity and flow.

## Steps

1. Identify logical entities from schema and screen/business docs.
2. Map each entity to a generic physical table and key columns.
3. Identify business flows, trigger screens, user actions, affected tables, and side effects.
4. Reference entities by `entity` name and tables by `physical_table`.
5. Mark uncertain business meaning as requiring human confirmation.

## Guardrails

- Use only local files.
- Use generic placeholder table names in examples and demos.
- Do not add exporter-specific fields to the entity or flow IR.
- Do not finalize business meaning.

## Human-Approval Points

- Humans confirm entity meaning, keys, and table mappings.
- Humans confirm flow steps, state transitions, and downstream side effects.

