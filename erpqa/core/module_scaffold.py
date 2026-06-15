from __future__ import annotations

from pathlib import Path

from .contracts import empty_contracts
from .memory import scaffold_module_memory
from .module_paths import module_dir, validate_module_name, write_module_yaml_if_missing
from .paths import ensure_qa_context
from .policy import scaffold_module_policy


def default_module_manifest(module: str) -> dict[str, object]:
    return {
        "module": module,
        "source_roots": {
            "spec": [f"extracted/{module}/spec"],
            "frontend": [f"extracted/{module}/frontend"],
            "backend": [f"extracted/{module}/backend"],
            "procedure": [f"extracted/{module}/procedure"],
        },
        "source": "erpqa module-init scaffold",
        "confidence": "medium",
        "needs_human_confirmation": True,
    }


def init_module(project_path: str | Path, module: str) -> list[Path]:
    module = validate_module_name(module)
    ensure_qa_context(project_path)
    root = module_dir(project_path, module)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "handoff").mkdir(parents=True, exist_ok=True)
    paths = [
        write_module_yaml_if_missing(project_path, module, "module_manifest.yaml", default_module_manifest(module)),
        scaffold_module_policy(project_path, module),
        scaffold_module_memory(project_path, module),
    ]
    for name, contract in empty_contracts(module).items():
        paths.append(write_module_yaml_if_missing(project_path, module, name, contract))
    return paths
