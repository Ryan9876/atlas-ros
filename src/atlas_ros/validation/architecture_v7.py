"""Static enforcement of the declarative Atlas ROS v7 layer boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

_LAYER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contracts/authority.py", ("atlas_ros.contracts",)),
    ("contracts/digests.py", ("atlas_ros.contracts",)),
    ("contracts/execution/", ("atlas_ros.contracts",)),
    ("contracts/migrations/", ("atlas_ros",)),
    ("policy/", ("atlas_ros.contracts", "atlas_ros.policy")),
    (
        "capabilities/",
        (
            "atlas_ros.capabilities",
            "atlas_ros.contracts",
            "atlas_ros.policy",
        ),
    ),
    (
        "application/",
        (
            "atlas_ros.application",
            "atlas_ros.capabilities",
            "atlas_ros.contracts",
            "atlas_ros.policy",
            "atlas_ros.ports",
        ),
    ),
    ("ports/", ("atlas_ros.contracts", "atlas_ros.ports")),
    (
        "kernel/",
        (
            "atlas_ros.application",
            "atlas_ros.capabilities",
            "atlas_ros.contracts",
            "atlas_ros.kernel",
            "atlas_ros.policy",
            "atlas_ros.ports",
        ),
    ),
    ("entry_points/", ("atlas_ros",)),
)

_FORBIDDEN_RUNTIME_IMPORTS = (
    "tools.release",
    "atlas_ros.adapters",
    "atlas_ros.intelligence",
    "atlas_ros.release",
)

_MIGRATION_FORBIDDEN_PREFIXES = (
    "application/",
    "capabilities/",
    "contracts/execution/",
    "entry_points/",
    "kernel/",
    "policy/",
    "ports/",
)


def imported_modules(path: Path) -> set[str]:
    """Return the absolute import modules found anywhere in one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def validate_v7(root: Path = PACKAGE_ROOT) -> list[dict[str, str]]:
    """Validate current v7-owned runtime files against their allowed dependencies."""
    violations: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        allowed = _allowed_prefixes(relative)
        if allowed is None:
            continue
        modules = imported_modules(path)
        for module in sorted(module for module in modules if module.startswith("atlas_ros")):
            if relative == "entry_points/_legacy.py" and module == "atlas_ros.cli":
                continue
            if module.startswith("atlas_ros.contracts.migrations") and relative.startswith(
                _MIGRATION_FORBIDDEN_PREFIXES
            ):
                violations.append(
                    {
                        "path": relative,
                        "import": module,
                        "rule": "production v7 layers cannot import compatibility migrations",
                    }
                )
                continue
            if not module.startswith(allowed):
                violations.append(
                    {
                        "path": relative,
                        "import": module,
                        "rule": "v7 layer import is outside the declarative allowlist",
                    }
                )
        if relative == "entry_points/main.py":
            for module in sorted(modules):
                if module.startswith(_FORBIDDEN_RUNTIME_IMPORTS):
                    violations.append(
                        {
                            "path": relative,
                            "import": module,
                            "rule": "lightweight runtime dispatcher cannot load heavy modules",
                        }
                    )
        text = path.read_text(encoding="utf-8")
        if "drive.google.com" in text or "Google_Drive" in text:
            violations.append(
                {
                    "path": relative,
                    "import": "Google Drive",
                    "rule": "current v7 runtime must not depend on Google Drive",
                }
            )
    return violations


def _allowed_prefixes(relative: str) -> tuple[str, ...] | None:
    for prefix, allowed in _LAYER_RULES:
        if relative == prefix or relative.startswith(prefix):
            return allowed
    return None
