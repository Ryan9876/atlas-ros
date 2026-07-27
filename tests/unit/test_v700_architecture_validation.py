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
