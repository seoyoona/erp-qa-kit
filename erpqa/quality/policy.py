from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from erpqa.core.yaml_io import load_yaml


@dataclass(frozen=True)
class QualityPolicy:
    forbidden_source_roots: tuple[str, ...] = ()
    impact_rules: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def load_quality_policy(path: str | Path) -> QualityPolicy:
    data = load_yaml(Path(path)) or {}
    return QualityPolicy(
        forbidden_source_roots=tuple(str(root) for root in data.get("forbidden_source_roots", [])),
        impact_rules=tuple(dict(rule) for rule in data.get("impact_rules", [])),
    )


def load_project_quality_policy(project_path: str | Path) -> QualityPolicy:
    path = Path(project_path) / "qa-context" / "quality_policy.yaml"
    if not path.exists():
        return QualityPolicy()
    return load_quality_policy(path)
