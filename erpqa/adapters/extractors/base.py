from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class RawExtraction:
    source_path: str
    kind: str
    records: list[dict[str, Any]]
    provenance_hint: str
    notes: list[str] = field(default_factory=list)
    adapter: str = ""


class Extractor(Protocol):
    name: str
    supported_extensions: frozenset[str]
    tier: str

    def available(self) -> bool:
        ...

    def extract(self, path: Path) -> RawExtraction:
        ...


def rel_source(path: Path) -> str:
    return path.as_posix()

