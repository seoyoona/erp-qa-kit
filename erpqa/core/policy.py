from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import CONFIDENCE_VALUES
from .errors import ErpqaError, UsageError
from .paths import qa_context_path, write_yaml_if_missing
from .yaml_io import load_yaml


ASPECTS = {
    "visible_text",
    "grid_columns",
    "form_fields",
    "search_filters",
    "procedure_mapping",
}
SOURCE_TOKENS = {"screen_spec", "backend", "procedure", "frontend"}
STEP_VOCABULARY = {
    "read_project_policy",
    "read_project_memory",
    "read_module_policy",
    "read_module_memory",
    "screen_spec_extraction",
    "frontend_contract_extraction",
    "screen_vs_frontend_comparison",
    "backend_mapping_check",
    "procedure_mapping_check",
    "data_flow_validation",
    "procedure_business_logic_validation",
    "cross_module_data_flow_validation",
}
READ_STEPS = [
    "read_project_policy",
    "read_project_memory",
    "read_module_policy",
    "read_module_memory",
]
REQUIRED_EXTRACTORS = {
    "xlsx_text",
    "xlsx_image_manifest",
    "csv",
    "markdown",
    "json_yaml",
    "frontend_static",
    "backend_static",
    "procedure_sql",
}


DEFAULT_POLICY: dict[str, Any] = {
    "qa_policy": {
        "name": "strict_screen_contract_first",
        "draft": True,
        "human_confirmed": False,
        "frontend_override_allowed": False,
        "review_strategy": "module_by_module",
        "source_of_truth": {
            "visible_text": {
                "primary": ["screen_spec", "backend"],
                "secondary": ["frontend"],
                "frontend_override_allowed": False,
            },
            "grid_columns": {
                "primary": ["screen_spec", "backend"],
                "secondary": ["frontend"],
                "frontend_override_allowed": False,
            },
            "form_fields": {
                "primary": ["screen_spec", "backend"],
                "secondary": ["frontend"],
                "frontend_override_allowed": False,
            },
            "search_filters": {
                "primary": ["screen_spec", "backend"],
                "secondary": ["frontend"],
                "frontend_override_allowed": False,
            },
            "procedure_mapping": {
                "primary": ["backend", "procedure"],
                "secondary": ["frontend", "screen_spec"],
                "frontend_override_allowed": False,
            },
        },
        "validation_order": [
            "read_project_policy",
            "read_project_memory",
            "read_module_policy",
            "read_module_memory",
            "screen_spec_extraction",
            "frontend_contract_extraction",
            "backend_mapping_check",
            "procedure_mapping_check",
            "screen_vs_frontend_comparison",
            "data_flow_validation",
            "procedure_business_logic_validation",
        ],
        "defer_until_frontend_verified": [
            "procedure_business_logic_validation",
            "cross_module_data_flow_validation",
        ],
        "forbidden_assumptions": [
            "Do not treat frontend implementation as correct if it conflicts with screen specs.",
            "Do not silently accept extra frontend columns.",
            "Do not override screen spec labels with frontend labels.",
            "Do not assume backend/procedure is correct without explicit evidence.",
        ],
        "allowed_file_formats": ["xlsx", "csv", "md", "json", "yaml", "yml", "sql"],
        "extraction_confidence_rules": {
            "default_needs_human_confirmation": True,
            "ocr_image": {
                "usable": True,
                "max_confidence": "medium",
                "needs_human_confirmation": True,
            },
        },
        "human_confirmation_requirements": {
            "require_for_low_confidence": True,
            "require_for_missing_policy_draft": True,
            "require_for_frontend_conflict": True,
            "require_for_deferred_areas": True,
        },
        "module_scope": {
            "strategy": "extracted_folder",
            "module_path_template": "{repo_root}/modules/{module}",
            "spec_glob": ["specs/**/*.xlsx", "specs/**/*.md"],
            "require_full_clone": False,
        },
        "repository_path_mapping": [
            {
                "repo": "ORD",
                "role": "mixed",
                "path": "extracted-folder://ORD",
                "extracted_folder": True,
                "trusted": False,
            },
            {
                "repo": "REPO_FRONTEND",
                "role": "frontend",
                "path": "extracted-folder://REPO_FRONTEND",
                "extracted_folder": True,
                "trusted": False,
            },
            {
                "repo": "REPO_BACKEND",
                "role": "backend",
                "path": "extracted-folder://REPO_BACKEND",
                "extracted_folder": True,
                "trusted": False,
            },
        ],
        "extractors": {
            "required": [
                {"name": "xlsx_text", "enabled": True, "extensions": ["xlsx"]},
                {"name": "xlsx_image_manifest", "enabled": True, "extensions": ["xlsx"]},
                {"name": "csv", "enabled": True, "extensions": ["csv"]},
                {"name": "markdown", "enabled": True, "extensions": ["md"]},
                {"name": "json_yaml", "enabled": True, "extensions": ["json", "yaml", "yml"]},
                {"name": "frontend_static", "enabled": True, "extensions": []},
                {"name": "backend_static", "enabled": True, "extensions": []},
                {"name": "procedure_sql", "enabled": True, "extensions": ["sql"]},
            ],
            "optional": [
                {"name": "pandas", "enabled": False, "extensions": ["xlsx", "csv"]},
                {"name": "markitdown", "enabled": False, "extensions": ["xlsx", "md"]},
            ],
            "future": [
                {"name": "docling", "enabled": False, "extensions": []},
                {"name": "unstructured", "enabled": False, "extensions": []},
            ],
        },
        "frontend_override": {
            "allowed_global": False,
            "may_override_screen_spec": False,
            "may_override_backend": False,
        },
    }
}

MODULE_POLICY_STUB = {
    "qa_policy": {
        "module": "",
        "inherits": "project_policy.yaml",
        "source": "erpqa module-init scaffold",
        "confidence": "medium",
        "needs_human_confirmation": True,
    }
}


@dataclass(frozen=True)
class EffectivePolicy:
    project_policy: dict[str, Any]
    module_policy: dict[str, Any]
    effective: dict[str, Any]
    project_policy_path: Path
    module_policy_path: Path | None
    warnings: tuple[str, ...] = ()

    @property
    def qa_policy(self) -> dict[str, Any]:
        return self.effective["qa_policy"]

    @property
    def is_draft(self) -> bool:
        policy = self.qa_policy
        return bool(policy.get("draft")) or policy.get("human_confirmed") is False

    def frontend_override_allowed(self, aspect: str) -> bool:
        policy = self.qa_policy
        global_allowed = bool(policy.get("frontend_override", {}).get("allowed_global", False))
        aspect_allowed = bool(
            policy.get("source_of_truth", {})
            .get(aspect, {})
            .get("frontend_override_allowed", False)
        )
        return global_allowed and aspect_allowed

    @property
    def validation_order(self) -> list[str]:
        return list(self.qa_policy.get("validation_order") or [])

    @property
    def deferred_steps(self) -> list[str]:
        return list(self.qa_policy.get("defer_until_frontend_verified") or [])

    @property
    def allowed_file_formats(self) -> set[str]:
        return {str(item).lower() for item in self.qa_policy.get("allowed_file_formats") or []}


def project_policy_path(project_path: str | Path) -> Path:
    return qa_context_path(project_path) / "project_policy.yaml"


def module_policy_path(project_path: str | Path, module: str) -> Path:
    return qa_context_path(project_path) / "modules" / module / "module_policy.yaml"


def scaffold_project_policy(project_path: str | Path) -> Path:
    return write_yaml_if_missing(project_path, "project_policy.yaml", DEFAULT_POLICY)


def scaffold_module_policy(project_path: str | Path, module: str) -> Path:
    data = deepcopy(MODULE_POLICY_STUB)
    data["qa_policy"]["module"] = module
    return write_yaml_if_missing(project_path, f"modules/{module}/module_policy.yaml", data)


def validate_policy_document(
    path: Path,
    data: Any,
    *,
    module: bool = False,
    project_policy: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("qa_policy"), dict):
        return [f"{path}: qa_policy: required mapping is missing"]
    policy = data["qa_policy"]
    if module:
        errors.extend(_validate_module_policy(path, policy, project_policy or {}))
        return errors

    required = [
        "name",
        "review_strategy",
        "source_of_truth",
        "validation_order",
        "defer_until_frontend_verified",
        "forbidden_assumptions",
        "allowed_file_formats",
        "extraction_confidence_rules",
        "human_confirmation_requirements",
        "module_scope",
        "repository_path_mapping",
        "extractors",
        "frontend_override",
    ]
    for key in required:
        if key not in policy:
            errors.append(f"{path}: qa_policy.{key}: required field is missing")
    if policy.get("review_strategy") not in {None, "module_by_module"}:
        errors.append(f"{path}: qa_policy.review_strategy: must be module_by_module")
    errors.extend(_validate_source_of_truth(path, policy))
    errors.extend(_validate_order(path, policy))
    errors.extend(_validate_confidence_rules(path, policy))
    errors.extend(_validate_extractors(path, policy))
    if "frontend_override_allowed" in policy and not isinstance(policy.get("frontend_override_allowed"), bool):
        errors.append(f"{path}: qa_policy.frontend_override_allowed: must be boolean")
    frontend_override = policy.get("frontend_override", {})
    for key in ("allowed_global", "may_override_screen_spec", "may_override_backend"):
        if not isinstance(frontend_override.get(key), bool):
            errors.append(f"{path}: qa_policy.frontend_override.{key}: must be boolean")
    if not isinstance(policy.get("repository_path_mapping"), list) or not policy.get("repository_path_mapping"):
        errors.append(f"{path}: qa_policy.repository_path_mapping: at least one mapping is required")
    return errors


def _validate_source_of_truth(path: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_of_truth = policy.get("source_of_truth", {})
    if not isinstance(source_of_truth, dict):
        return [f"{path}: qa_policy.source_of_truth: must be a mapping"]
    for aspect in ASPECTS:
        item = source_of_truth.get(aspect)
        if not isinstance(item, dict):
            errors.append(f"{path}: qa_policy.source_of_truth.{aspect}: required mapping is missing")
            continue
        primary = item.get("primary")
        secondary = item.get("secondary")
        if not isinstance(primary, list) or not primary:
            errors.append(f"{path}: qa_policy.source_of_truth.{aspect}.primary: non-empty list required")
        if not isinstance(secondary, list):
            errors.append(f"{path}: qa_policy.source_of_truth.{aspect}.secondary: list required")
        primary_set = set(primary or [])
        secondary_set = set(secondary or [])
        for token in primary_set | secondary_set:
            if token not in SOURCE_TOKENS:
                errors.append(f"{path}: qa_policy.source_of_truth.{aspect}: unknown source token {token}")
        if primary_set & secondary_set:
            errors.append(f"{path}: qa_policy.source_of_truth.{aspect}: source cannot be primary and secondary")
        if not isinstance(item.get("frontend_override_allowed"), bool):
            errors.append(
                f"{path}: qa_policy.source_of_truth.{aspect}.frontend_override_allowed: must be boolean"
            )
    return errors


def _validate_order(path: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    order = policy.get("validation_order")
    defer = policy.get("defer_until_frontend_verified")
    if not isinstance(order, list):
        return [f"{path}: qa_policy.validation_order: list required"]
    if order[:4] != READ_STEPS:
        errors.append(f"{path}: qa_policy.validation_order: read steps must appear first in order")
    for step in order:
        if step not in STEP_VOCABULARY:
            errors.append(f"{path}: qa_policy.validation_order: unknown step {step}")
    if not isinstance(defer, list):
        errors.append(f"{path}: qa_policy.defer_until_frontend_verified: list required")
    else:
        for step in defer:
            if step not in STEP_VOCABULARY:
                errors.append(f"{path}: qa_policy.defer_until_frontend_verified: unknown step {step}")
            elif step not in order and step != "cross_module_data_flow_validation":
                errors.append(f"{path}: qa_policy.defer_until_frontend_verified: {step} not in validation_order")
    return errors


def _validate_confidence_rules(path: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rules = policy.get("extraction_confidence_rules", {})
    ocr = rules.get("ocr_image", {}) if isinstance(rules, dict) else {}
    if ocr.get("max_confidence") not in {"low", "medium"}:
        errors.append(f"{path}: qa_policy.extraction_confidence_rules.ocr_image.max_confidence: must be low or medium")
    if ocr.get("needs_human_confirmation") is not True:
        errors.append(
            f"{path}: qa_policy.extraction_confidence_rules.ocr_image.needs_human_confirmation: must be true"
        )
    return errors


def _validate_extractors(path: Path, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = set(policy.get("allowed_file_formats") or [])
    for item in allowed:
        if not isinstance(item, str) or item.startswith(".") or item.lower() != item:
            errors.append(f"{path}: qa_policy.allowed_file_formats: invalid format {item}")
    extractors = policy.get("extractors", {})
    required = extractors.get("required", []) if isinstance(extractors, dict) else []
    names = {item.get("name") for item in required if isinstance(item, dict)}
    missing = REQUIRED_EXTRACTORS - names
    for name in sorted(missing):
        errors.append(f"{path}: qa_policy.extractors.required: missing required extractor {name}")
    for tier_name in ("required", "optional", "future"):
        entries = extractors.get(tier_name, []) if isinstance(extractors, dict) else []
        if entries is None:
            continue
        if not isinstance(entries, list):
            errors.append(f"{path}: qa_policy.extractors.{tier_name}: must be a list")
            continue
        for item in entries:
            if not isinstance(item, dict):
                errors.append(f"{path}: qa_policy.extractors.{tier_name}: extractor entry must be mapping")
                continue
            for ext in item.get("extensions") or []:
                if ext not in allowed:
                    errors.append(
                        f"{path}: qa_policy.extractors.{tier_name}.{item.get('name')}.extensions: {ext} not allowed"
                    )
    for item in required:
        if not isinstance(item, dict):
            errors.append(f"{path}: qa_policy.extractors.required: extractor entry must be mapping")
            continue
        if item.get("enabled") is not True:
            errors.append(f"{path}: qa_policy.extractors.required.{item.get('name')}: must be enabled")
    return errors


def _validate_module_policy(path: Path, policy: dict[str, Any], project: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project_qp = project.get("qa_policy", {}) if isinstance(project, dict) else {}
    if policy.get("review_strategy") == "full_project":
        errors.append(f"{path}: qa_policy.review_strategy: module policy cannot set full_project")
    project_frontend = project_qp.get("frontend_override", {})
    frontend = policy.get("frontend_override", {})
    for key in ("allowed_global", "may_override_screen_spec", "may_override_backend"):
        if frontend.get(key) is True and project_frontend.get(key) is False:
            errors.append(f"{path}: qa_policy.frontend_override.{key}: module cannot grant frontend override")
    project_sot = project_qp.get("source_of_truth", {})
    for aspect, item in (policy.get("source_of_truth") or {}).items():
        if item.get("frontend_override_allowed") is True and (
            project_sot.get(aspect, {}).get("frontend_override_allowed") is False
        ):
            errors.append(
                f"{path}: qa_policy.source_of_truth.{aspect}.frontend_override_allowed: module cannot grant frontend override"
            )
    project_ocr = (
        project_qp.get("extraction_confidence_rules", {})
        .get("ocr_image", {})
    )
    module_ocr = (
        policy.get("extraction_confidence_rules", {})
        .get("ocr_image", {})
    )
    rank = {"low": 0, "medium": 1, "high": 2}
    if module_ocr.get("usable") is True and project_ocr.get("usable") is False:
        errors.append(f"{path}: qa_policy.extraction_confidence_rules.ocr_image.usable: module cannot loosen OCR use")
    if module_ocr.get("needs_human_confirmation") is False:
        errors.append(
            f"{path}: qa_policy.extraction_confidence_rules.ocr_image.needs_human_confirmation: must stay true"
        )
    if "max_confidence" in module_ocr and rank.get(module_ocr["max_confidence"], 9) > rank.get(
        project_ocr.get("max_confidence", "medium"),
        1,
    ):
        errors.append(
            f"{path}: qa_policy.extraction_confidence_rules.ocr_image.max_confidence: module cannot raise confidence cap"
        )
    for item in (policy.get("extractors", {}).get("required") or []):
        if isinstance(item, dict) and item.get("enabled") is False:
            errors.append(f"{path}: qa_policy.extractors.required.{item.get('name')}: module cannot disable required extractor")
    for field in ("source", "confidence", "needs_human_confirmation"):
        if field in policy:
            continue
        if policy:
            errors.append(f"{path}: qa_policy.{field}: module policy provenance field is required")
    confidence = policy.get("confidence")
    if confidence is not None and confidence not in CONFIDENCE_VALUES:
        errors.append(f"{path}: qa_policy.confidence: must be high, medium, or low")
    if confidence in {"low", "medium"} and policy.get("needs_human_confirmation") is False:
        errors.append(f"{path}: qa_policy.needs_human_confirmation: low/medium confidence must require confirmation")
    return errors


def merge_policy(project_policy: dict[str, Any], module_policy: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(project_policy)
    module_qp = (module_policy or {}).get("qa_policy", {})
    if not module_qp:
        return merged
    target = merged.setdefault("qa_policy", {})
    for key, value in module_qp.items():
        if key in {"module", "inherits", "source", "confidence", "needs_human_confirmation"}:
            continue
        if key in {"forbidden_assumptions", "defer_until_frontend_verified"} and isinstance(value, list):
            existing = list(target.get(key) or [])
            for item in value:
                if item not in existing:
                    existing.append(item)
            target[key] = existing
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            target[key] = _deep_merge(target[key], value)
        else:
            target[key] = deepcopy(value)
    return merged


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_effective_policy(
    project_path: str | Path,
    module: str | None = None,
    *,
    allow_draft: bool = False,
) -> EffectivePolicy:
    project_path = Path(project_path)
    project_path_value = project_policy_path(project_path)
    if not project_path_value.exists():
        raise ErpqaError("project_policy.yaml is missing; run `erpqa policy-init <project_path>` first")
    project_doc = load_yaml(project_path_value)
    project_errors = validate_policy_document(project_path_value, project_doc)
    if project_errors:
        raise ErpqaError("; ".join(project_errors))

    module_doc: dict[str, Any] = {}
    module_path_value: Path | None = None
    if module is not None:
        module_path_value = module_policy_path(project_path, module)
        if not module_path_value.exists():
            raise ErpqaError(f"module policy is missing for module {module}; run `erpqa module-init` first")
        loaded = load_yaml(module_path_value) or {}
        module_doc = loaded if isinstance(loaded, dict) else {}
        module_errors = validate_policy_document(
            module_path_value,
            module_doc,
            module=True,
            project_policy=project_doc,
        )
        if module_errors:
            raise ErpqaError("; ".join(module_errors))

    effective = merge_policy(project_doc, module_doc)
    result = EffectivePolicy(
        project_policy=project_doc,
        module_policy=module_doc,
        effective=effective,
        project_policy_path=project_path_value,
        module_policy_path=module_path_value,
    )
    if result.is_draft and not allow_draft:
        raise ErpqaError("project_policy.yaml is a draft requiring human confirmation; set draft: false and human_confirmed: true after review")
    return result


def confirm_policy_for_tests(project_path: str | Path) -> None:
    """Helper used by tests/fixtures; not exposed on the CLI."""
    path = project_policy_path(project_path)
    data = load_yaml(path) or {}
    data.setdefault("qa_policy", {})["draft"] = False
    data.setdefault("qa_policy", {})["human_confirmed"] = True
    from .paths import write_yaml

    write_yaml(project_path, "project_policy.yaml", data)
