from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas_ros.adapters.llm import FixtureLLMAdapter
from atlas_ros.contracts import (
    CaptureEnvelope,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionStep,
    KnowledgePackage,
    ManagementPackage,
    ReasoningPackage,
    ReconciliationResult,
)
from atlas_ros.domain.models import Action, Capture, Classification, RoutingRecommendation
from atlas_ros.legacy import (
    W01CaptureFacade,
    W02RoutingFacade,
    W03ADecompositionFacade,
    W03TodoistFacade,
)
from atlas_ros.runtime.database import RuntimeDatabase
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


def test_semantic_packages_preserve_component_boundaries() -> None:
    reasoning = ReasoningPackage(
        source_component="engines.management_reasoning",
        classification="action",
        destination="action_records",
        confidence=0.95,
        rationale=["Ryan-owned executable outcome"],
    )
    knowledge = KnowledgePackage(
        source_component="engines.knowledge_composition",
        module_ids=["leadership-core"],
        facts={"audience": "leadership team"},
    )
    management = ManagementPackage(
        source_component="engines.management_structure",
        responsibility="Lead the operating review",
        desired_outcome="A reviewed and approved operating plan",
        owner="Ryan",
    )
    assert reasoning.requires_human_decision is False
    assert knowledge.module_ids == ["leadership-core"]
    assert management.owner == "Ryan"


def test_execution_plan_requires_contiguous_sequence() -> None:
    valid = ExecutionPlan(
        source_component="planning.execution",
        action_id="A-1",
        objective="Publish the reviewed release",
        destination="Todoist/Work",
        steps=[
            ExecutionStep(step_id="S-1", title="Validate", done_when="Checks pass", sequence=1)
        ],
    )
    assert valid.steps[0].sequence == 1

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


def test_execution_receipt_and_reconciliation_fail_closed() -> None:
    verified = ExecutionReceipt(
        source_component="orchestration.execution",
        action_id="A-1",
        provider="todoist",
        provider_object_id="task-1",
        applied=True,
        readback_verified=True,
    )
    assert verified.applied is True

    with pytest.raises(ValidationError, match="verified readback"):
        ExecutionReceipt(
            source_component="orchestration.execution",
            action_id="A-1",
            provider="todoist",
            provider_object_id="task-1",
            applied=True,
            readback_verified=False,
        )

    consistent = ReconciliationResult(
        source_component="services.reconciliation",
        object_id="task-1",
        consistent=True,
        checkpoint_advanced=True,
    )
    assert consistent.checkpoint_advanced is True

    with pytest.raises(ValidationError, match="checkpoint cannot advance"):
        ReconciliationResult(
            source_component="services.reconciliation",
            correlation_id=uuid4(),
            object_id="task-1",
            consistent=False,
            mismatches=["priority differs"],
            checkpoint_advanced=True,
        )


def test_legacy_facades_delegate_without_behavior_change(tmp_path: Path) -> None:
    database = RuntimeDatabase(tmp_path / "runtime.db")
    database.initialize()
    captured = W01CaptureFacade(database).capture("Prepare the operating review")
    assert captured.content == "Prepare the operating review"

    recommendation = RoutingRecommendation(
        classification=Classification.ACTION,
        destination="action_records",
        confidence=1.0,
        desired_outcome="Operating review is ready",
    )
    routed = W02RoutingFacade(FixtureLLMAdapter(recommendation)).plan(
        Capture(content="Prepare the operating review")
    )
    assert routed == recommendation

    action = Action(
        id="A-1",
        title="Prepare operating review",
        owner="Ryan",
        definition_of_done="Operating review is ready",
        execution_ready=True,
        delegation_reviewed=True,
    )
    assert W03ADecompositionFacade().readiness(action).status.value == "ready"
    assert W03TodoistFacade().plan(action).action_id == "A-1"


def test_current_architecture_has_no_forbidden_dependencies() -> None:
    assert validate() == []
