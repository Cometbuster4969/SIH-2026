"""Tool registry — loads config/registry.yaml and serves GET /tools data."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .schemas import RegistryFile, TaskType, ToolSpec

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "config" / "registry.yaml"


@lru_cache(maxsize=4)
def load_registry(path: str | Path | None = None) -> RegistryFile:
    p = Path(path) if path else DEFAULT_REGISTRY
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    reg = RegistryFile.model_validate(raw)
    if not reg.tools:
        raise ValueError(f"registry at {p} declares no tools")
    return reg


def get_tool(name: str) -> ToolSpec:
    for t in load_registry().tools:
        if t.name == name:
            return t
    raise KeyError(f"tool '{name}' not in registry")


def tool_for_task(task: TaskType) -> ToolSpec:
    for t in load_registry().tools:
        if t.task == task:
            return t
    raise KeyError(f"no tool registered for task {task}")


def tools_summary() -> list[dict]:
    """Payload for GET /tools — public, safe to return as JSON."""
    return [t.model_dump(mode="json") for t in load_registry().tools]
