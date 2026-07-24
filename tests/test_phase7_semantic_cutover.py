# ruff: noqa: I001
from pathlib import Path

from atlas_ros.capabilities import (
    CaptureService,
    DecompositionService,
    ExecutionPlanner,
    ExecutionReconciliationService,
    RecordRoutingService,
    TodoistService,
)
from atlas_ros.validation.architecture import validate
from atlas_ros.workflows import (
    CaptureService as LegacyCaptureService,
    DecompositionService as LegacyDecompositionService,
    TodoistReconciliationService as LegacyReconciliationService,
    TodoistService as LegacyTodoistService,
)


def test_semantic_capability_surface_is_importable() -> None:
    assert CaptureService is LegacyCaptureService
    assert DecompositionService is LegacyDecompositionService
    assert TodoistService is LegacyTodoistService
    assert issubclass(ExecutionReconciliationService, LegacyReconciliationService)
    assert ExecutionPlanner.__name__ == "ExecutionPlanner"
    assert RecordRoutingService.__name__ == "RecordRoutingService"


def test_new_internal_code_cannot_import_w_modules(tmp_path: Path) -> None:
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
            "rule": "new internal code must use semantic capability imports",
        }
    ]


def test_archival_mapping_is_present() -> None:
    mapping = Path("docs/migration/W_WORKFLOW_ARCHIVAL_MAPPING.md").read_text(encoding="utf-8")
    assert "W01 capture" in mapping
    assert "Execution Reconciliation Service" in mapping
    assert "Alias retained" in mapping
