import importlib.util
from pathlib import Path

import atlas_ros.capabilities as capabilities
from atlas_ros.contracts.migrations.capability_surface_v6 import (
    CanonicalReconciliationService,
    CaptureService,
    DecompositionService,
    ExecutionPlanner,
    RecordRoutingService,
    TodoistService,
)
from atlas_ros.validation.architecture import validate


def test_historical_capability_surface_is_migration_only() -> None:
    assert CaptureService.__name__ == "CaptureService"
    assert DecompositionService.__name__ == "DecompositionService"
    assert TodoistService.__name__ == "TodoistService"
    assert CanonicalReconciliationService.__name__ == "CanonicalReconciliationService"
    assert ExecutionPlanner.__name__ == "ExecutionPlanner"
    assert RecordRoutingService.__name__ == "RecordRoutingService"
    assert not hasattr(capabilities, "CaptureService")
    assert importlib.util.find_spec("atlas_ros.workflows") is None
    assert importlib.util.find_spec("atlas_ros.legacy") is None


def test_retired_workflow_imports_are_rejected(tmp_path: Path) -> None:
    package = tmp_path / "atlas_ros"
    (package / "feature").mkdir(parents=True)
    (package / "feature" / "bad.py").write_text(
        "from atlas_ros.workflows.w03_todoist import TodoistService\n",
        encoding="utf-8",
    )
    violations = validate(package)
    assert violations == [
        {
            "path": (package / "feature" / "bad.py").as_posix(),
            "import": "atlas_ros.workflows.w03_todoist",
            "rule": "retired workflow and legacy packages cannot be imported in v6",
        }
    ]


def test_archival_mapping_is_present() -> None:
    mapping = Path("docs/migration/W_WORKFLOW_ARCHIVAL_MAPPING.md").read_text(encoding="utf-8")
    assert "W01 capture" in mapping
    assert "Execution Reconciliation Service" in mapping
    assert "Retired in v6.0.0" in mapping
