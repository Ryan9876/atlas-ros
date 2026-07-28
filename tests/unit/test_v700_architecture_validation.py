from __future__ import annotations

from pathlib import Path

from atlas_ros.validation.architecture_v7 import validate_v7


def test_current_v7_owned_modules_follow_declarative_layer_rules() -> None:
    assert validate_v7() == []


def test_contract_layer_rejects_kernel_dependency(tmp_path: Path) -> None:
    contract = tmp_path / "contracts" / "execution" / "invalid.py"
    contract.parent.mkdir(parents=True)
    contract.write_text("from atlas_ros.kernel import RuntimeKernel\n", encoding="utf-8")

    violations = validate_v7(tmp_path)

    assert violations == [
        {
            "path": "contracts/execution/invalid.py",
            "import": "atlas_ros.kernel",
            "rule": "v7 layer import is outside the declarative allowlist",
        }
    ]


def test_migration_boundary_may_reference_historical_runtime(tmp_path: Path) -> None:
    migration = tmp_path / "contracts" / "migrations" / "v6.py"
    migration.parent.mkdir(parents=True)
    migration.write_text("from atlas_ros.planning import ExecutionPlanner\n", encoding="utf-8")

    assert validate_v7(tmp_path) == []


def test_application_rejects_compatibility_migration_import(tmp_path: Path) -> None:
    application = tmp_path / "application" / "invalid.py"
    application.parent.mkdir(parents=True)
    application.write_text(
        "from atlas_ros.contracts.migrations.capability_surface_v6 import CaptureService\n",
        encoding="utf-8",
    )

    assert validate_v7(tmp_path) == [
        {
            "path": "application/invalid.py",
            "import": "atlas_ros.contracts.migrations.capability_surface_v6",
            "rule": "production v7 layers cannot import compatibility migrations",
        }
    ]


def test_lightweight_dispatcher_rejects_direct_provider_import(tmp_path: Path) -> None:
    entry_point = tmp_path / "entry_points" / "main.py"
    entry_point.parent.mkdir(parents=True)
    entry_point.write_text("import atlas_ros.adapters.todoist\n", encoding="utf-8")

    violations = validate_v7(tmp_path)

    assert violations[-1] == {
        "path": "entry_points/main.py",
        "import": "atlas_ros.adapters.todoist",
        "rule": "lightweight runtime dispatcher cannot load heavy modules",
    }
