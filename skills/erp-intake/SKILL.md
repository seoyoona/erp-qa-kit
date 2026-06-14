# ERP Intake Skill

## Purpose

Propose a source inventory for a local ERP project folder. The output is a
human-reviewable classification of files into docs, DB schema, API specs, screen
specs, backend, and frontend sources.

## Inputs

- Target ERP project folder, read-only.
- Existing `qa-context/project_manifest.yaml`, if present.
- Existing `qa-context/source_inventory.md`, if present.

## Outputs

- Draft `qa-context/source_inventory.md`.
- Draft inventory section in `qa-context/project_manifest.yaml`.
- Provenance trio on every inferred inventory item: `source`, `confidence`,
  `needs_human_confirmation`.

## Steps

1. Walk the target folder while excluding `qa-context/` and VCS/cache folders.
2. Classify each file into exactly one of the six allowed categories.
3. Infer a likely module only from local path/content evidence.
4. Mark uncertain classifications with `confidence: low` and
   `needs_human_confirmation: true`.
5. Write only draft artifacts under `qa-context/`.

## Guardrails

- Do not modify any target ERP source file.
- Do not call network services or runtime LLM APIs.
- Do not invent categories beyond the six allowed categories.
- Do not treat inferred classifications as final business truth.

## Human-Approval Points

- Humans confirm module ownership and source classification.
- Humans decide whether low/medium-confidence items can be trusted.

