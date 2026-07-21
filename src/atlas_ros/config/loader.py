from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import yaml


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


@lru_cache(maxsize=32)
def _load_config(name: str, root: str = "") -> Any:
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("invalid configuration name")
    if root:
        path = Path(root).resolve() / f"{name}.yaml"
        raw = path.read_text(encoding="utf-8")
    else:
        raw = files("atlas_ros.data").joinpath(f"{name}.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"configuration {name} must be a mapping")
    return _freeze(data)


def _thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def load_config(name: str, root: Path | None = None) -> dict[str, Any]:
    """Return an isolated mutable copy of immutable cached policy data."""
    return cast(dict[str, Any], _thaw(_load_config(name, str(root.resolve()) if root else "")))
