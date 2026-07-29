#!/usr/bin/env python3
"""Prove production runtime modules do not import development tooling."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path("src/atlas_ros")
DEVTOOLS = ROOT / "devtools_cli"
ALLOWED = {ROOT / "entry_points" / "dev.py"}


def main() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        if DEVTOOLS in path.parents or path in ALLOWED:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                module = ",".join(alias.name for alias in node.names)
            if "atlas_ros.devtools_cli" in module:
                violations.append(f"{path}:{getattr(node, 'lineno', 0)}")
    if violations:
        raise SystemExit("production imports development tooling: " + ", ".join(violations))
    print("development-tooling boundary valid")


if __name__ == "__main__":
    main()
