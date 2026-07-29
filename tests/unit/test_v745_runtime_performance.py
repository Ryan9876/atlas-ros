"""Deterministic tests for the v7.4.5 Runtime Performance Foundation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from atlas_ros.runtime_performance import (
    IncrementalComputationReceiptV1,
    OperationalComputationGraphV1,
    OperationalComputationNodeV1,
    OperationalDependencyEdgeV1,
    PerformanceBudgetV1,
    PerformanceObservationV1,
    ProviderReadMetricsV1,
    ReadRequirementV1,
    RuntimeDependencyDeclarationV1,
    VerifiedRuntimeBundleV1,
    build_operation_snapshot,
    compile_read_plan,
    compile_runtime_composition,
    plan_incremental_computation,
)
from atlas_ros.runtime_performance.contracts import ProviderReadReceiptV1, ProviderRecordV1


def _record(*, content: str = "open", revision: str = "1") -> ProviderRecordV1:
    return ProviderRecordV1(
        provider="notion",
        canonical_record_id="action:1",
        source_record_id="page-1",
        source_revision=revision,
        source_timestamp="2026-07-29T00:00:00Z",
        read_timestamp="2026-07-29T00:01:00Z",
        requested_fields=("Status", "Owner"),
        missing_fields=("Owner",),
        normalized_content={"Status": content},
        provenance=("collection://actions",),
    )


def _receipt(*, complete: bool = True) -> ProviderReadReceiptV1:
    return ProviderReadReceiptV1(
        provider="notion",
        request_id="read-1",
        record_identities=("page-1",),
        requested_fields=("Status", "Owner"),
        returned_records=1,
        complete=complete,
        pagination_complete=complete,
        provider_revision="1",
        read_timestamp="2026-07-29T00:01:00Z",
    )


def test_snapshot_is_deterministic_and_preserves_missing_fields() -> None:
    first = build_operation_snapshot(
        operation_id="op-1",
        correlation_id="corr-1",
        requested_scope=("actions",),
        authoritative_release_identity="v7.4.0@6d48b93",
        provider_records=(_record(),),
        provider_read_receipts=(_receipt(),),
    )
    second = build_operation_snapshot(
        operation_id="op-1",
        correlation_id="corr-1",
        requested_scope=("actions",),
        authoritative_release_identity="v7.4.0@6d48b93",
        provider_records=(_record(),),
        provider_read_receipts=(_receipt(),),
    )
    assert first.snapshot_digest == second.snapshot_digest
    assert first.missing_fields == ("Owner",)
    assert first.authoritative is False
    assert first.reusable_across_operations is False


def test_snapshot_marks_contradictory_provider_content() -> None:
    snapshot = build_operation_snapshot(
        operation_id="op-1",
        correlation_id="corr-1",
        requested_scope=("actions",),
        authoritative_release_identity="v7.4.0@6d48b93",
        provider_records=(_record(content="open"), _record(content="closed")),
        provider_read_receipts=(_receipt(),),
    )
    assert snapshot.contradictory_record_ids == ("action:1",)


def test_read_plan_coalesces_duplicate_and_overlapping_requirements() -> None:
    plan = compile_read_plan(
        operation_id="op-1",
        requirements=(
            ReadRequirementV1(
                requesting_capability="brief",
                provider="notion",
                record_type="action",
                record_identities=("page-1",),
                required_fields=("Status",),
                batching_supported=True,
            ),
            ReadRequirementV1(
                requesting_capability="context",
                provider="notion",
                record_type="action",
                record_identities=("page-1",),
                required_fields=("Owner",),
                batching_supported=True,
            ),
        ),
    )
    assert plan.expected_read_count == 1
    assert plan.duplicate_requests_removed == 1
    assert plan.required_fields == ("Owner", "Status")
    assert plan.requesting_capabilities == ("brief", "context")


def test_read_plan_reports_conflicting_conditional_revisions() -> None:
    plan = compile_read_plan(
        operation_id="op-1",
        requirements=(
            ReadRequirementV1(
                requesting_capability="brief",
                provider="notion",
                record_type="action",
                record_identities=("page-1",),
                conditional_revision="1",
            ),
            ReadRequirementV1(
                requesting_capability="context",
                provider="notion",
                record_type="action",
                record_identities=("page-1",),
                conditional_revision="2",
            ),
        ),
    )
    assert plan.incomplete_requirements


def test_verified_bundle_rejects_digest_mismatch() -> None:
    with pytest.raises(ValidationError, match="digest mismatch"):
        VerifiedRuntimeBundleV1(
            compiled_policy_registry={"policy": "digest"},
            validated_contract_registry={},
            validated_capability_registry={},
            validated_schemas={},
            command_to_capability_bindings={},
            capability_dependency_metadata={},
            architecture_identity="arch-1",
            source_commit="abc",
            package_version="7.4.5",
            compiler_versions={"atlas": "1"},
            source_file_digests={"policy.yaml": "digest"},
            registry_digests={"policy": "digest"},
            bundle_digest="incorrect",
        )


def test_performance_contracts_cannot_suppress_correctness_or_fabricate() -> None:
    with pytest.raises(ValidationError, match="correctness gates"):
        PerformanceBudgetV1(
            release_version="7.4.5",
            metric="startup_ms",
            maximum=1000,
            unit="ms",
            workload="ordinary-command",
            evidence_source="baseline",
            correctness_gates_suppressible=True,
        )
    with pytest.raises(ValidationError, match="fabricated"):
        ProviderReadMetricsV1(
            provider_round_trips=1,
            records_requested=1,
            records_returned=1,
            duplicate_reads_eliminated=0,
            fabricated_measurements=True,
        )


def test_telemetry_is_behavior_neutral_and_redacted() -> None:
    with pytest.raises(ValidationError, match="behavior-neutral"):
        PerformanceObservationV1(
            operation_id="op-1",
            release_identity="v7.4.5",
            workload="brief",
            telemetry_redacted=False,
        )


def test_scoped_composition_unions_dependencies() -> None:
    plan = compile_runtime_composition(
        command="brief",
        declarations=(
            RuntimeDependencyDeclarationV1(
                command="brief",
                capability="operating_brief",
                contracts=("BriefV1",),
                policies=("brief-policy",),
                schemas=("actions",),
                ports=("notion-read",),
                adapters=("notion",),
            ),
            RuntimeDependencyDeclarationV1(
                command="brief",
                capability="commitments",
                contracts=("CommitmentV1",),
                policies=("commitment-policy",),
                schemas=("delegated-work",),
                ports=("notion-read",),
                adapters=("notion",),
            ),
        ),
    )
    assert plan.full_composition_requirement is False
    assert plan.required_capabilities == ("commitments", "operating_brief")
    assert plan.required_adapters == ("notion",)


def test_consequential_or_incomplete_composition_broadens() -> None:
    plan = compile_runtime_composition(
        command="execute",
        declarations=(
            RuntimeDependencyDeclarationV1(
                command="execute",
                capability="execution",
                consequential=True,
                complete=False,
            ),
        ),
    )
    assert plan.full_composition_requirement is True
    assert "consequential command" in plan.broadening_reasons
    assert "incomplete dependency declaration" in plan.broadening_reasons


def test_unknown_command_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown command"):
        compile_runtime_composition(command="unknown", declarations=())


def _node(node_id: str, *, revision: str = "1", result: str = "r") -> OperationalComputationNodeV1:
    return OperationalComputationNodeV1(
        node_id=node_id,
        canonical_record_id=node_id,
        source_revision=revision,
        normalized_content_digest=f"content-{revision}",
        policy_digest="policy-1",
        contract_version="1",
        capability_version="1",
        result_digest=result,
    )


def test_incremental_change_recomputes_transitive_dependents() -> None:
    prior = (_node("delegated"), _node("commitment"), _node("brief"))
    graph = OperationalComputationGraphV1(
        nodes=(_node("delegated", revision="2"), _node("commitment"), _node("brief")),
        edges=(
            OperationalDependencyEdgeV1(
                source_node_id="delegated", dependent_node_id="commitment"
            ),
            OperationalDependencyEdgeV1(source_node_id="commitment", dependent_node_id="brief"),
        ),
        authority_identity="authority-1",
        schema_identity="schema-1",
        redaction_policy_digest="redaction-1",
    )
    plan = plan_incremental_computation(
        current_graph=graph,
        prior_nodes=prior,
        prior_authority_identity="authority-1",
        prior_schema_identity="schema-1",
        prior_redaction_policy_digest="redaction-1",
    )
    assert plan.changed_node_ids == ("delegated",)
    assert plan.recompute_node_ids == ("brief", "commitment", "delegated")
    assert plan.full_recomputation_required is False


def test_authority_change_forces_full_recomputation() -> None:
    graph = OperationalComputationGraphV1(
        nodes=(_node("action"), _node("brief")),
        edges=(OperationalDependencyEdgeV1(source_node_id="action", dependent_node_id="brief"),),
        authority_identity="authority-2",
        schema_identity="schema-1",
        redaction_policy_digest="redaction-1",
    )
    plan = plan_incremental_computation(
        current_graph=graph,
        prior_nodes=graph.nodes,
        prior_authority_identity="authority-1",
        prior_schema_identity="schema-1",
        prior_redaction_policy_digest="redaction-1",
    )
    assert plan.full_recomputation_required is True
    assert plan.recompute_node_ids == ("action", "brief")
    assert "authority identity changed" in plan.fallback_reasons


def test_incremental_receipt_cannot_make_index_authoritative() -> None:
    with pytest.raises(ValidationError, match="non-authoritative"):
        IncrementalComputationReceiptV1(
            operation_id="op-1",
            plan_digest="digest",
            evaluated_node_ids=("action",),
            reused_node_ids=(),
            full_recomputation_performed=False,
            equivalence_verified=True,
            persisted_index_authoritative=True,
        )
