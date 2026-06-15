from __future__ import annotations

from pathlib import Path

from .errors import UsageError
from .paths import qa_output_path, write_text, write_text_if_missing, write_yaml, write_yaml_if_missing


def validate_module_name(module: str) -> str:
    if not module or "/" in module or "\\" in module or module in {".", ".."}:
        raise UsageError(f"invalid module name: {module!r}")
    return module


def module_relative(module: str, relative_path: str | Path = "") -> Path:
    module = validate_module_name(module)
    return Path("modules") / module / relative_path


def module_dir(project_path: str | Path, module: str) -> Path:
    return qa_output_path(project_path, module_relative(module))


def module_output_path(project_path: str | Path, module: str, relative_path: str | Path) -> Path:
    return qa_output_path(project_path, module_relative(module, relative_path))


def module_contract_path(project_path: str | Path, module: str, contract_name: str) -> Path:
    return module_output_path(project_path, module, contract_name)


def module_report_path(project_path: str | Path, module: str, report_name: str) -> Path:
    return module_output_path(project_path, module, Path("reports") / report_name)


def module_handoff_path(project_path: str | Path, module: str, handoff_name: str) -> Path:
    return module_output_path(project_path, module, Path("handoff") / handoff_name)


def write_module_text(project_path: str | Path, module: str, relative_path: str | Path, text: str) -> Path:
    return write_text(project_path, module_relative(module, relative_path), text)


def write_module_text_if_missing(
    project_path: str | Path,
    module: str,
    relative_path: str | Path,
    text: str,
) -> Path:
    return write_text_if_missing(project_path, module_relative(module, relative_path), text)


def write_module_yaml(project_path: str | Path, module: str, relative_path: str | Path, data: object) -> Path:
    return write_yaml(project_path, module_relative(module, relative_path), data)


def write_module_yaml_if_missing(
    project_path: str | Path,
    module: str,
    relative_path: str | Path,
    data: object,
) -> Path:
    return write_yaml_if_missing(project_path, module_relative(module, relative_path), data)
