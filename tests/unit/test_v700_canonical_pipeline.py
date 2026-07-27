from __future__ import annotations

import sys

import pytest

from atlas_ros.application.canonical_processing import CanonicalProcessingCoordinator
from atlas_ros.application.pipeline import (
    CanonicalPipelineError,
    CanonicalPreAuthorizationPipeline,
    canonical_pre_authorization_stages,
)
from atlas_ros.capabilities.input_processing import DeterministicInputProcessor
from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope
from atlas_ros.contracts.execution.transaction import PlannedProviderOperation


def pipeline() -> CanonicalPreAuthorizationPipeline:
    return CanonicalPreAuthorizationPipeline(
        CanonicalProcessingCoordinator(
            release_version="7.0.0rc1",
            source_commit="a" * 40,
            initializer_version="7.0",
            contract_catalog_digest="b" * 64,
            policy_registry_digest="c" * 64,
            capability_catalog_digest="d" * 64,
            stages=canonical_pre_authorization_stages(),
        )
    )


def envelope() -> CaptureEnvelope:
    return CaptureEnvelope(
        source="test",
        content=(
            "Launch the governed pilot. "
            "Implement the approved checkpoint. "
            "Never execute without attended authorization."
        ),
    )


def explicit_operation(capture: CaptureEnvelope) -> PlannedProviderOperation:
    graph = DeterministicInputProcessor().process(capture)
    action = next(node for node in graph.nodes if node.execution_candidate)
    return PlannedProviderOperation(
        operation_id=action.node_id,
        sequence=0,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest=sha256_digest({"title": action.title}),
        idempotency_key=f"{capture.correlation_id}:{action.node_id}",
    )


def test_pipeline_runs_every_provider_neutral_stage_once() -> None:
    capture = envelope()
    result = pipeline().process(
        capture,
        provider_requests=(explicit_operation(capture),),
        framework_rules=("attended_only", "readback_required", "attended_only"),
        scenario_ids=("current", "reduced_scope"),
    )

    expected_stages = tuple(stage.name for stage in canonical_pre_authorization_stages())
    assert tuple(result.lineage.stage_digests) == expected_stages
    assert result.state.graph is not None
    assert result.state.classification is not None
    assert result.state.knowledge is not None
    assert result.state.management_reasoning is not None
    assert result.state.management_structure is not None
    assert result.state.routing is not None
    assert result.state.framework is not None
    assert result.state.minimum_effective_path is not None
    assert result.state.decision_support is not None
    assert result.state.scenario_analysis is not None
    assert result.state.proposed_plan is not None
    assert result.state.proposed_plan.blockers == ()
    assert result.state.proposed_plan.operations[0].provider == "todoist"
    assert result.state.framework.warnings == ("duplicate_rules_removed",)
    assert result.presentation.audit_digest
    assert result.lineage.authorization_id is None
    assert result.lineage.execution_transaction_id is None
    assert result.lineage.provider_operation_receipts == ()


def test_pipeline_without_explicit_provider_request_blocks_instead_of_inventing_work() -> None:
    result = pipeline().process(envelope())

    assert result.state.proposed_plan is not None
    assert result.state.proposed_plan.operations == ()
    assert result.state.proposed_plan.blockers
    assert all(
        blocker.startswith("explicit_provider_operation_required:")
        for blocker in result.state.proposed_plan.blockers
    )


def test_pipeline_rejects_operation_not_bound_to_execution_candidate() -> None:
    capture = envelope()
    operation = PlannedProviderOperation(
        operation_id="not-a-graph-action",
        sequence=0,
        provider="todoist",
        action="create",
        target="Work/Active Projects",
        payload_digest="a" * 64,
        idempotency_key="capture:invalid",
    )

    with pytest.raises(ValueError, match="execution-candidate action nodes"):
        pipeline().process(capture, provider_requests=(operation,))


def test_pipeline_rejects_noncanonical_stage_order() -> None:
    stages = canonical_pre_authorization_stages()
    invalid = CanonicalPreAuthorizationPipeline(
        CanonicalProcessingCoordinator(
            release_version="7.0.0rc1",
            source_commit="a" * 40,
            initializer_version="7.0",
            contract_catalog_digest="b" * 64,
            policy_registry_digest="c" * 64,
            capability_catalog_digest="d" * 64,
            stages=tuple(reversed(stages)),
        )
    )

    with pytest.raises(CanonicalPipelineError, match="canonical"):
        invalid.process(envelope())


def test_pipeline_imports_no_provider_adapters() -> None:
    for module_name in tuple(sys.modules):
        if module_name.startswith("atlas_ros.adapters"):
            del sys.modules[module_name]

    pipeline().process(envelope())

    assert not any(
        name == "atlas_ros.adapters" or name.startswith("atlas_ros.adapters.")
        for name in sys.modules
    )
