from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .memory import EffectiveMemory, load_effective_memory
from .policy import EffectivePolicy, load_effective_policy


@dataclass(frozen=True)
class RunContext:
    project_path: Path
    module: str | None
    policy: EffectivePolicy
    memory: EffectiveMemory


def load_context(
    project_path: str | Path,
    module: str | None = None,
    *,
    allow_draft_policy: bool = False,
) -> RunContext:
    root = Path(project_path).resolve()
    policy = load_effective_policy(root, module, allow_draft=allow_draft_policy)
    memory = load_effective_memory(root, module)
    return RunContext(project_path=root, module=module, policy=policy, memory=memory)
