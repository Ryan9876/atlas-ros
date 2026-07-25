from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PREFIXES: dict[str, tuple[str, ...]] = {
    "contracts": ("atlas_ros.adapters", "atlas_ros.workflows", "atlas_ros.legacy"),
    "engines": ("atlas_ros.adapters", "atlas_ros.legacy"),
    "planning": (
        "atlas_ros.adapters",
        "atlas_ros.legacy",
        "atlas_ros.orchestration",
    ),
    "orchestration": ("atlas_ros.adapters", "atlas_ros.planning"),
    "policy": ("atlas_ros.adapters", "atlas_ros.legacy"),
}
LEGACY_WORKFLOW_PREFIX = "atlas_ros.workflows.w"
LEGACY_IMPORT_ALLOWLIST = {
    "capabilities/__init__.py",
    "legacy/facades.py",
    "services/execution_reconciliation.py",
}
NON_EXECUTING_ENGINES = {
    "engines/management_reasoning.py",
    "engines/classification_intelligence.py",
    "engines/knowledge_composition.py",
    "engines/management_structure.py",
}
FORBIDDEN_NON_EXECUTING_SYMBOLS = {
    "ExecutionPlan",
    "ExecutionStep",
    "TodoistAdapter",
    "NotionAdapter",
}
PLANNER_FORBIDDEN_SYMBOLS = {
    "ExecutionAuthorization",
    "ExecutionOrchestrator",
    "ExecutionReceipt",
    "TodoistExecutionAdapter",
}
ADAPTER_FORBIDDEN_CONSTRUCTORS = {
    "ExecutionAuthorization",
    "ExecutionAuthorizationV2",
    "ExecutionPlan",
    "ExecutionPlanV2",
}
ORCHESTRATOR_FORBIDDEN_CONSTRUCTORS = {
    "ExecutionStep",
    "ExecutionStepV2",
}
RECEIPT_CONSTRUCTORS = {"ExecutionReceipt", "ExecutionReceiptV2"}
EXECUTION_CONSTRUCTORS = {"ExecutionPlan", "ExecutionPlanV2"}
EXECUTION_CONSTRUCTOR_ALLOWLIST = {
    "contracts/execution_v2.py",
    "planning/execution.py",
}
PROVIDER_ID_FIELDS = {
    "provider_object_id",
    "todoist_id",
    "project_id",
    "section_id",
    "label_id",
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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        if calls & EXECUTION_CONSTRUCTORS and relative not in EXECUTION_CONSTRUCTOR_ALLOWLIST:
            violations.append(
                {
                    "path": path.as_posix(),
                    "import": ",".join(sorted(calls & EXECUTION_CONSTRUCTORS)),
                    "rule": "only the canonical Execution Planner may propose plans",
                }
            )
        if relative.startswith("engines/") and calls & {
            "ExecutionPlan",
            "ExecutionPlanV2",
            "ExecutionStep",
            "ExecutionStepV2",
        }:
            violations.append(
                {
                    "path": path.as_posix(),
                    "import": ",".join(
                        sorted(
                            calls
                            & {
                                "ExecutionPlan",
                                "ExecutionPlanV2",
                                "ExecutionStep",
                                "ExecutionStepV2",
                            }
                        )
                    ),
                    "rule": "reasoning, knowledge, and structure engines cannot create tasks",
                }
            )
        if relative.startswith("planning/"):
            names = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import | ast.ImportFrom)
                for alias in node.names
            }
            forbidden_names = names & PLANNER_FORBIDDEN_SYMBOLS
            if forbidden_names:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(sorted(forbidden_names)),
                        "rule": "planner cannot authorize, transact, or produce receipts",
                    }
                )
            authorized_true = any(
                isinstance(node, ast.keyword)
                and node.arg == "authorized"
                and isinstance(node.value, ast.Constant)
                and node.value.value is True
                for node in ast.walk(tree)
            )
            environment_calls = any(
                isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}
                for node in ast.walk(tree)
            )
            if authorized_true or environment_calls:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": "authorization",
                        "rule": "planner cannot hide authorization in code or environment",
                    }
                )
        if relative == "contracts/execution_v2.py":
            fields = {
                node.target.id
                for node in ast.walk(tree)
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            }
            provider_fields = fields & PROVIDER_ID_FIELDS
            if provider_fields:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(sorted(provider_fields)),
                        "rule": "Execution Plan V2 contracts cannot store provider object IDs",
                    }
                )
        if relative.startswith("adapters/") and relative != "adapters/__init__.py":
            names = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import | ast.ImportFrom)
                for alias in node.names
            }
            if names & {"ExecutionPlanner", "ExecutionPlanningPolicy"}:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(
                            sorted(names & {"ExecutionPlanner", "ExecutionPlanningPolicy"})
                        ),
                        "rule": "provider adapters cannot decide whether tasks should exist",
                    }
                )
            adapter_calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            forbidden_constructors = adapter_calls & ADAPTER_FORBIDDEN_CONSTRUCTORS
            if forbidden_constructors:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(sorted(forbidden_constructors)),
                        "rule": "provider adapters cannot construct plans or authorization",
                    }
                )
            for module in sorted(imported_modules(path)):
                module_name = module.rsplit(".", 1)[-1]
                if (
                    module.startswith("atlas_ros.adapters.")
                    and module_name not in {"errors", "keychain"}
                    and not path.stem.startswith(module_name)
                ):
                    violations.append(
                        {
                            "path": path.as_posix(),
                            "import": module,
                            "rule": "provider adapters cannot import another provider adapter",
                        }
                    )
        if relative.startswith("orchestration/"):
            orchestration_calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            forbidden_steps = orchestration_calls & ORCHESTRATOR_FORBIDDEN_CONSTRUCTORS
            if forbidden_steps:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(sorted(forbidden_steps)),
                        "rule": "orchestration cannot create or re-plan execution steps",
                    }
                )
        receipt_calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        } & RECEIPT_CONSTRUCTORS
        if receipt_calls and not (
            relative.startswith("orchestration/")
            or relative in {"contracts/models.py", "contracts/orchestration_v2.py"}
        ):
            violations.append(
                {
                    "path": path.as_posix(),
                    "import": ",".join(sorted(receipt_calls)),
                    "rule": "canonical execution receipts are emitted only by orchestration",
                }
            )
        if relative == "workflows/w03_todoist.py":
            forbidden_provider_calls = {
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and node.attr in {"create_task", "update_task", "execute_operation"}
            }
            if forbidden_provider_calls:
                violations.append(
                    {
                        "path": path.as_posix(),
                        "import": ",".join(sorted(forbidden_provider_calls)),
                        "rule": "W03 must remain a compatibility facade over orchestration",
                    }
                )
    return violations
