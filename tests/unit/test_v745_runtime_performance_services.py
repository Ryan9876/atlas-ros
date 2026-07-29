from __future__ import annotations

import pytest

from atlas_ros.runtime_performance.contracts import (
    OperationalComputationGraphV1,
    OperationalComputationNodeV1,
    OperationalDependencyEdgeV1,
    ProviderReadReceiptV1,
    ProviderRecordV1,
    ReadRequirementV1,
    RuntimeDependencyDeclarationV1,
)
from atlas_ros.runtime_performance.services import (
    CapabilityScopedComposer,
    IncrementalOperationalPlanner,
    NonAuthoritativeIncrementalIndex,
    OperationSnapshotCoordinator,
    RuntimeBundleBuilder,
    RuntimeBundleVerifier,
)


class FixtureAdapter:
    def execute_read_plan(self, plan):
        records = tuple(
            ProviderRecordV1(
                provider="notion",
                canonical_record_id=identity,
                source_record_id=f"source-{identity}",
                source_revision="r1",
                read_timestamp="2026-07-29T00:00:00Z",
                requested_fields=plan.required_fields,
                normalized_content={field: "value" for field in plan.required_fields},
                provenance=("fixture",),
            )
            for identity in plan.requested_record_identities
        )
        receipt = ProviderReadReceiptV1(
            provider="notion",
            request_id="request-1",
            record_identities=plan.requested_record_identities,
            requested_fields=plan.required_fields,
            returned_records=len(records),
            complete=True,
            pagination_complete=True,
            read_timestamp="2026-07-29T00:00:00Z",
        )
        return records, (receipt,)


def test_operation_snapshot_coordinator_reads_once_and_freezes() -> None:
    coordinator = OperationSnapshotCoordinator("7.4.0@immutable")
    requirements = (
        ReadRequirementV1(
            requesting_capability="brief",
            provider="notion",
            record_type="action",
            record_identities=("A-1",),
            required_fields=("status",),
        ),
        ReadRequirementV1(
            requesting_capability="context",
            provider="notion",
            record_type="action",
            record_identities=("A-1",),
            required_fields=("owner",),
        ),
    )
    plan, snapshot = coordinator.execute(
        operation_id="op-1",
        correlation_id="corr-1",
        requested_scope=("actions",),
        requirements=requirements,
        adapters={"notion": FixtureAdapter()},
    )
    assert plan.expected_read_count == 1
    assert plan.duplicate_requests_removed == 1
    assert snapshot.canonical_record_references == ("A-1",)
    assert snapshot.authoritative is False


def test_operation_snapshot_coordinator_blocks_missing_adapter() -> None:
    coordinator = OperationSnapshotCoordinator("7.4.0@immutable")
    requirement = ReadRequirementV1(
        requesting_capability="brief",
        provider="notion",
        record_type="action",
        record_identities=("A-1",),
    )
    with pytest.raises(ValueError, match="missing read adapter"):
        coordinator.execute(
            operation_id="op-1",
            correlation_id="corr-1",
            requested_scope=("actions",),
            requirements=(requirement,),
            adapters={},
        )


def test_runtime_bundle_build_verify_and_source_fallback() -> None:
    builder = RuntimeBundleBuilder(
        architecture_identity="arch-1",
        source_commit="source-1",
        package_version="7.4.5",
        compiler_versions={"registry": "1"},
    )
    bundle = builder.build(
        policies={"authority": "policy-digest"},
        contracts={"snapshot": "contract-digest"},
        capabilities={"read": "capability-digest"},
        schemas={"snapshot": "schema-digest"},
        command_bindings={"status": "read"},
        dependencies={"read": ("snapshot",)},
        source_file_digests={"policy.yaml": "file-digest"},
    )
    verifier = RuntimeBundleVerifier("source-1", "7.4.5", "arch-1")
    loaded, source = verifier.load_or_compile(bundle=bundle, source_compiler=lambda: bundle)
    assert loaded == bundle
    assert source == "verified_bundle"

    fallback_verifier = RuntimeBundleVerifier("source-1", "7.4.5", "arch-1")
    loaded, source = fallback_verifier.load_or_compile(bundle=None, source_compiler=lambda: bundle)
    assert loaded == bundle
    assert source == "canonical_source_fallback"


def test_scoped_composition_equivalence_and_broadening() -> None:
    declarations = (
        RuntimeDependencyDeclarationV1(
            command="status",
            capability="operational-awareness",
            contracts=("snapshot",),
            policies=("authority",),
            schemas=("action",),
            ports=("notion-read",),
            adapters=("notion",),
        ),
    )
    composer = CapabilityScopedComposer(declarations)
    assert composer.verify_equivalence("status")
    assert not composer.compose("status").full_composition_requirement
    assert composer.compose("status", force_full=True).full_composition_requirement


def test_incremental_index_is_disposable_and_transitive() -> None:
    prior_nodes = tuple(
        OperationalComputationNodeV1(
            node_id=node_id,
            canonical_record_id=node_id,
            source_revision="r1",
            normalized_content_digest=f"content-{node_id}",
            policy_digest="policy-1",
            contract_version="1",
            capability_version="1",
        )
        for node_id in ("leaf", "parent", "brief")
    )
    current_nodes = (
        prior_nodes[0].model_copy(update={"source_revision": "r2"}),
        prior_nodes[1],
        prior_nodes[2],
    )
    graph = OperationalComputationGraphV1(
        nodes=current_nodes,
        edges=(
            OperationalDependencyEdgeV1(source_node_id="leaf", dependent_node_id="parent"),
            OperationalDependencyEdgeV1(source_node_id="parent", dependent_node_id="brief"),
        ),
        authority_identity="authority-1",
        schema_identity="schema-1",
        redaction_policy_digest="redaction-1",
    )
    index = NonAuthoritativeIncrementalIndex(
        authority_identity="authority-1",
        schema_identity="schema-1",
        redaction_policy_digest="redaction-1",
        nodes=prior_nodes,
    )
    plan = IncrementalOperationalPlanner().plan(current_graph=graph, prior_index=index)
    assert plan.recompute_node_ids == ("brief", "leaf", "parent")
    assert not plan.full_recomputation_required

    full = IncrementalOperationalPlanner().plan(current_graph=graph, prior_index=None)
    assert full.full_recomputation_required
    assert full.recompute_node_ids == ("brief", "leaf", "parent")


def test_incremental_index_cannot_be_authoritative() -> None:
    with pytest.raises(ValueError, match="cannot be authoritative"):
        NonAuthoritativeIncrementalIndex(
            authority_identity="authority-1",
            schema_identity="schema-1",
            redaction_policy_digest="redaction-1",
            nodes=(),
            authoritative=True,
        )
