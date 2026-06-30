from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Iterable

from erpqa.core.paths import write_yaml
from erpqa.core.yaml_io import load_yaml


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str
    allowed: bool


def _is_allowed(rel: str, allowed_roots: Iterable[str]) -> bool:
    return any(rel == root or rel.startswith(root.rstrip("/") + "/") for root in allowed_roots)


def _hash_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_file_snapshot(project_path: str | Path, allowed_roots: list[str]) -> dict:
    root = Path(project_path).resolve()
    records: dict[str, dict] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        records[rel] = {
            "size": path.stat().st_size,
            "sha256": _hash_file(path),
            "allowed": _is_allowed(rel, allowed_roots),
        }
    return {"project_path": str(root), "allowed_roots": allowed_roots, "files": records}


def compare_file_snapshots(before: dict, after: dict) -> dict:
    b = before.get("files", {})
    a = after.get("files", {})
    added = sorted(set(a) - set(b))
    removed = sorted(set(b) - set(a))
    modified = sorted(key for key in set(a) & set(b) if a[key].get("sha256") != b[key].get("sha256"))
    unexpected_added = [path for path in added if not a[path].get("allowed")]
    unexpected_removed = [path for path in removed if not b[path].get("allowed")]
    unexpected_modified = [path for path in modified if not a[path].get("allowed")]
    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unexpected_added": unexpected_added,
        "unexpected_removed": unexpected_removed,
        "unexpected_modified": unexpected_modified,
        "pass": not (unexpected_added or unexpected_removed or unexpected_modified),
    }


def git_status(repo_path: str | Path) -> dict:
    repo = Path(repo_path)
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--short", "--branch"],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "repo": str(repo),
        "returncode": proc.returncode,
        "stdout": proc.stdout.splitlines(),
        "stderr": proc.stderr.splitlines(),
    }


def write_isolation_snapshot(project_path: str | Path, label: str, repos: list[str]) -> Path:
    snapshot = collect_file_snapshot(project_path, allowed_roots=["qa-context", "extracted"])
    snapshot["git_status"] = [git_status(repo) for repo in repos]
    relative = Path("safety") / f"{label}_snapshot.yaml"
    write_yaml(project_path, relative, snapshot)
    return Path(project_path) / "qa-context" / relative


def write_isolation_comparison(project_path: str | Path, before_label: str, after_label: str) -> tuple[Path, dict]:
    root = Path(project_path)
    before = load_yaml(root / "qa-context" / "safety" / f"{before_label}_snapshot.yaml")
    after = load_yaml(root / "qa-context" / "safety" / f"{after_label}_snapshot.yaml")
    diff = compare_file_snapshots(before or {}, after or {})
    out = write_yaml(project_path, "safety/isolation_verification.yaml", diff)
    return out, diff
