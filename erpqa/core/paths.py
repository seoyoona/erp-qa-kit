from __future__ import annotations

from pathlib import Path

from .constants import QA_CONTEXT_DIR
from .errors import UsageError, WriteOutsideQaContextError
from .yaml_io import dump_yaml


SCAFFOLD_DIRS = [
    "rules",
    "generated/sql",
    "reports",
    "feedback",
    "handoff",
]


def resolve_project_path(project_path: str | Path, must_exist: bool = True) -> Path:
    path = Path(project_path).expanduser()
    if must_exist and (not path.exists() or not path.is_dir()):
        raise UsageError(f"project_path must be an existing directory: {project_path}")
    return path.resolve()


def qa_context_path(project_path: str | Path) -> Path:
    return Path(project_path).resolve() / QA_CONTEXT_DIR


def ensure_qa_context(project_path: str | Path) -> Path:
    qa = qa_context_path(project_path)
    qa.mkdir(parents=True, exist_ok=True)
    for rel in SCAFFOLD_DIRS:
        (qa / rel).mkdir(parents=True, exist_ok=True)
    return qa


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_within_qa_context(project_path: str | Path, output_path: Path) -> Path:
    qa = qa_context_path(project_path).resolve()
    resolved = output_path.resolve()
    if not is_relative_to(resolved, qa):
        raise WriteOutsideQaContextError(
            f"refusing to write outside qa-context: {output_path}"
        )
    return resolved


def qa_output_path(project_path: str | Path, relative_path: str | Path) -> Path:
    qa = qa_context_path(project_path)
    candidate = qa / relative_path
    return assert_within_qa_context(project_path, candidate)


def write_text(project_path: str | Path, relative_path: str | Path, text: str) -> Path:
    target = qa_output_path(project_path, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def write_text_if_missing(project_path: str | Path, relative_path: str | Path, text: str) -> Path:
    target = qa_output_path(project_path, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(text, encoding="utf-8")
    return target


def write_yaml(project_path: str | Path, relative_path: str | Path, data: object) -> Path:
    return write_text(project_path, relative_path, dump_yaml(data))


def write_yaml_if_missing(project_path: str | Path, relative_path: str | Path, data: object) -> Path:
    return write_text_if_missing(project_path, relative_path, dump_yaml(data))

