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
NON_EXECUTING_ENGINES = {
    "engines/knowledge_composition.py",
    "engines/management_structure.py",
}
FORBIDDEN_NON_EXECUTING_SYMBOLS = {
    "ExecutionPlan",
    "ExecutionStep",
    "TodoistAdapter",
    "NotionAdapter",
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
        if relative in NON_EXECUTING_ENGINES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            names = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import | ast.ImportFrom)
                for alias in node.names
            }
            for symbol in sorted(names & FORBIDDEN_NON_EXECUTING_SYMBOLS):
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": symbol,
                        "rule": "knowledge and structure engines must remain non-executing",
                    }
                )
            literals = {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            if "team-operating-model" in literals:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": "team-operating-model",
                        "rule": "generic engines must not hard-code a planning model",
                    }
                )
    return violations
