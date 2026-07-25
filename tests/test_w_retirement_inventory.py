import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "inventory_w_references.py"
SPEC = importlib.util.spec_from_file_location("inventory_w_references", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
inventory_w_references = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_w_references)


def test_inventory_excludes_immutable_rollback_source(tmp_path: Path) -> None:
    runtime = tmp_path / "src" / "atlas_ros"
    runtime.mkdir(parents=True)
    (runtime / "current.py").write_text("VALUE = 1\n", encoding="utf-8")

    rollback = tmp_path / "rollback-source" / "atlas_ros-5.6.0rc1" / "src" / "atlas_ros"
    rollback.mkdir(parents=True)
    (rollback / "w03_todoist.py").write_text(
        "from atlas_ros.workflows.w03_todoist import TodoistService  # W03\n",
        encoding="utf-8",
    )

    inventory = inventory_w_references.build_inventory(tmp_path)

    assert inventory["runtime_w_module_count"] == 0
    assert inventory["blocking_reference_count"] == 0
    assert all(
        not str(item["path"]).startswith("rollback-source/")
        for item in inventory["references"]
    )


def test_inventory_still_blocks_active_source_references(tmp_path: Path) -> None:
    runtime = tmp_path / "src" / "atlas_ros"
    runtime.mkdir(parents=True)
    (runtime / "current.py").write_text(
        "from atlas_ros.workflows.w03_todoist import TodoistService\n",
        encoding="utf-8",
    )

    inventory = inventory_w_references.build_inventory(tmp_path)

    assert inventory["runtime_w_module_count"] == 0
    assert inventory["blocking_reference_count"] == 1
    assert inventory["blocking_references"][0]["path"] == "src/atlas_ros/current.py"
