from __future__ import annotations

import hashlib
from pathlib import Path
import shutil


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO = REPO_ROOT / "examples" / "pipe-manufacturing-demo"


def copy_demo(tmp_path: Path) -> Path:
    target = tmp_path / "pipe-manufacturing-demo"
    shutil.copytree(DEMO, target)
    return target


def snapshot_outside_qa(project: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for file in sorted(project.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(project)
        if rel.parts and rel.parts[0] == "qa-context":
            continue
        snapshot[rel.as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return snapshot

