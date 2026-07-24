from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas_ros.contracts import (
    CaptureEnvelope,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionStep,
    ReconciliationResult,
)
from scripts.validate_architecture import validate


def test_capture_envelope_is_versioned_and_immutable() -> None:
    envelope = CaptureEnvelope(
        source_component="legacy.w01",
        source="cli",
        content="Prepare the operating review",
    )
    assert envelope.contract_version == 1
    assert envelope.contract_kind.value == "capture"
    with pytest.raises(ValidationError):
        envelope.content = "changed"


def test_execution_plan_requires_contiguous_sequence() -> None:
    with pytest.raises(ValidationError, match="contiguous one-based sequence"):
        ExecutionPlan(
            source_component="planning.execution",
            action_id="A-1",
            objective="Publish the reviewed release",
            destination="Todoist/Work",
            steps=[
                ExecutionStep(step_id="S-1", title="Validate", done_when="Checks pass", sequence=2)
            ],
        )


def test_applied_receipt_requires_readback() -> None:
    with pytest.raises(ValidationError, match="verified readback"):
        ExecutionReceipt(
            source_component="orchestration.execution",
            action_id="A-1",
            provider="todoist",
            provider_object_id="task-1",
            applied=True,
            readback_verified=False,
        )


def test_reconciliation_checkpoint_fails_closed() -> None:
    with pytest.raises(ValidationError, match="checkpoint cannot advance"):
        ReconciliationResult(
            source_component="services.reconciliation",
            correlation_id=uuid4(),
            object_id="task-1",
            consistent=False,
            mismatches=["priority differs"],
            checkpoint_advanced=True,
        )


def test_current_architecture_has_no_forbidden_dependencies() -> None:
    assert validate() == []
