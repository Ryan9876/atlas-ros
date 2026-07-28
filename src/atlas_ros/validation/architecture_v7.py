"""Static enforcement of the declarative Atlas ROS v7 layer boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

_LAYER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contracts/authority.py", ("atlas_ros.contracts",)),
    ("contracts/compiler.py", ("atlas_ros.contracts",)),
    ("contracts/digests.py", ("atlas_ros.contracts",)),
    ("contracts/history.py", ("atlas_ros.contracts",)),
    ("contracts/release.py", ("atlas_ros.contracts",)),
    ("contracts/registry.py", ("atlas_ros.contracts",)),
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
        "adapters/",
        (
            "atlas_ros.adapters",
            "atlas_ros.contracts",
            "atlas_ros.ports",
        ),
    ),
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
    (
        "runtime/",
        (
            "atlas_ros.capabilities",
            "atlas_ros.contracts",
            "atlas_ros.domain",
            "atlas_ros.policy",
            "atlas_ros.runtime",
        ),
    ),
    ("entry_points/", ("atlas_ros",)),
)

# These inherited adapters remain only for migration and regression coverage.
_HISTORICAL_ADAPTERS = frozenset(
    {
        "adapters/llm.py",
        "adapters/notion_execution.py",
        "adapters/todoist_execution.py",
    }
)

_FORBIDDEN_RUNTIME_IMPORTS = (
    "tools.release",
    "atlas_ros.adapters",
    "atlas_ros.cli",
    "atlas_ros.contracts.migrations",
    "atlas_ros.entry_points._legacy",
    "atlas_ros.intelligence",
    "atlas_ros.release",
)

_COMPATIBILITY_ENTRY_POINTS = frozenset(
    {
        "entry_points/_legacy.py",
        "entry_points/migrate.py",
        "entry_points/release.py",
    }
)

_MIGRATION_FORBIDDEN_PREFIXES = (
    "adapters/",
    "application/",
    "capabilities/",
    "contracts/execution/",
    "entry_points/",
    "kernel/",
    "policy/",
    "ports/",
    "runtime/",
)


class _RuntimeImportVisitor(ast.NodeVisitor):
    """Collect imports while excluding branches guarded only by TYPE_CHECKING."""

    def __init__(self) -> None:
        self.modules: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        self.modules.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.modules.add(node.module)

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            for item in node.orelse:
                self.visit(item)
            return
        self.generic_visit(node)


def imported_modules(path: Path) -> set[str]:
    """Return runtime import modules found in one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _RuntimeImportVisitor()
    visitor.visit(tree)
    return visitor.modules


def validate_v7(root: Path = PACKAGE_ROOT) -> list[dict[str, str]]:
    """Validate current v7-owned runtime files against their allowed dependencies."""
    violations: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if root == PACKAGE_ROOT and relative in _HISTORICAL_ADAPTERS:
            continue
        allowed = _allowed_prefixes(relative)
        if allowed is None:
            continue
        modules = imported_modules(path)
        for module in sorted(module for module in modules if module.startswith("atlas_ros")):
            if relative in _COMPATIBILITY_ENTRY_POINTS:
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


def _is_type_checking_guard(node: ast.expr) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "typing"
        and node.attr == "TYPE_CHECKING"
    )


def _allowed_prefixes(relative: str) -> tuple[str, ...] | None:
    for prefix, allowed in _LAYER_RULES:
        if relative == prefix or relative.startswith(prefix):
            return allowed
    return None
