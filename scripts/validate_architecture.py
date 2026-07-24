from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path("src/atlas_ros")
FORBIDDEN_PREFIXES: dict[str, tuple[str, ...]] = {
    "contracts": ("atlas_ros.adapters", "atlas_ros.workflows", "atlas_ros.legacy"),
    "engines": ("atlas_ros.adapters", "atlas_ros.legacy"),
    "planning": ("atlas_ros.adapters", "atlas_ros.legacy"),
    "policy": ("atlas_ros.adapters", "atlas_ros.legacy"),
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


def validate(root: Path = ROOT) -> list[dict[str, str]]:
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
    return violations


def main() -> None:
    violations = validate()
    print(json.dumps({"valid": not violations, "violations": violations}, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
