from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES: dict[str, tuple[str, ...]] = {
    "contracts": ("atlas_ros.adapters", "atlas_ros.workflows", "atlas_ros.legacy"),
    "engines": ("atlas_ros.adapters", "atlas_ros.legacy"),
    "planning": ("atlas_ros.adapters", "atlas_ros.legacy"),
    "policy": ("atlas_ros.adapters", "atlas_ros.legacy"),
}
LEGACY_WORKFLOW_PREFIX = "atlas_ros.workflows.w"
LEGACY_IMPORT_ALLOWLIST = {
    "capabilities/__init__.py",
    "legacy/facades.py",
    "services/execution_reconciliation.py",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def validate(root: Path = PACKAGE_ROOT) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for layer, forbidden in FORBIDDEN_PREFIXES.items():
        layer_root = root / layer
        if not layer_root.exists():
            continue
        for path in sorted(layer_root.rglob("*.py")):
            for module in sorted(imported_modules(path)):
                matched = next((prefix for prefix in forbidden if module.startswith(prefix)), "")
                if matched:
                    violations.append(
                        {
                            "path": path.as_posix(),
                            "import": module,
                            "rule": f"{layer} must not depend on {matched}",
                        }
                    )
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("workflows/") or relative in LEGACY_IMPORT_ALLOWLIST:
            continue
        for module in sorted(imported_modules(path)):
            if module.startswith(LEGACY_WORKFLOW_PREFIX):
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": module,
                        "rule": "new internal code must use semantic capability imports",
                    }
                )
    return violations
