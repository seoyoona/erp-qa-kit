from __future__ import annotations

from pathlib import Path

from .paths import ensure_qa_context, write_text_if_missing, write_yaml_if_missing


MANIFEST_STUB = {
    "project": {
        "name": "unclassified-project",
        "target_root": ".",
        "source": "erpqa init scaffold",
        "confidence": "low",
        "needs_human_confirmation": True,
    },
    "modules": [],
    "source_inventory": [],
    "category_counts": {},
}

ENTITY_MAP_STUB = {"entities": []}
FLOW_MAP_STUB = {"flows": []}
FEEDBACK_ITEMS_STUB = {"feedback_items": []}

PM_TEMPLATE = """# PM Feedback Template

Use this file to draft observations before converting them into feedback_items.yaml.

## Feedback item
- Title:
- Module:
- Related flow:
- Related rule:
- Severity proposal (BLOCKER/MAJOR/MINOR):
- Observed behavior:
- Expected behavior:
- Actual behavior:
- Reproduction steps:
- Evidence:
- Affected records:
- Suspected area:
- AI fix instruction:
- Validation after fix:
- Source:
- Confidence (high/medium/low):
- Needs human confirmation: true
"""

RULE_TEMPLATE = """# Add human-reviewed rule YAML files here.
# Required shape:
# rules:
#   - rule_id: example_rule
#     name: Example rule
#     module: inventory
#     flow: example_flow
#     severity: MAJOR
#     verification_type: DB_ASSERTION
#     description: Example rule description.
#     expected_result: Zero rows means pass.
#     required_entities: []
#     required_tables: []
#     sql: null
#     source: "human-authored template"
#     confidence: low
#     needs_human_confirmation: true
"""


def init_project(project_path: str | Path) -> list[Path]:
    ensure_qa_context(project_path)
    created_or_existing = [
        write_yaml_if_missing(project_path, "project_manifest.yaml", MANIFEST_STUB),
        write_yaml_if_missing(project_path, "entity_map.yaml", ENTITY_MAP_STUB),
        write_yaml_if_missing(project_path, "flow_map.yaml", FLOW_MAP_STUB),
        write_yaml_if_missing(project_path, "feedback/feedback_items.yaml", FEEDBACK_ITEMS_STUB),
        write_text_if_missing(project_path, "feedback/PM_FEEDBACK_TEMPLATE.md", PM_TEMPLATE),
        write_text_if_missing(project_path, "rules/README.md", RULE_TEMPLATE),
    ]
    return created_or_existing

