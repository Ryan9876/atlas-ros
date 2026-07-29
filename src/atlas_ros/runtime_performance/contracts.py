"""Immutable runtime-performance contracts and deterministic pure planners.

These models optimize repeated reads and computation without becoming release,
provider, authorization, or execution authority. All planning is sequential.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


class ImmutableContract(BaseModel):
    """Strict immutable base for runtime-performance contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def digest(self) -> str:
        return _digest(self.model_dump(mode="json", exclude_none=True))


class ProviderReadReceiptV1(ImmutableContract):
    schema_version: str = "provider-read-receipt-v1"
    provider: str
    request_id: str
    record_identities: tuple[str, ...] = Field(default_factory=tuple)
    requested_fields: tuple[str, ...] = Field(default_factory=tuple)
    returned_records: int = Field(ge=0)
    complete: bool
    pagination_complete: bool
    provider_revision: str | None = None
    bytes_read: int | None = Field(default=None, ge=0)
    read_timestamp: str
    limitations: tuple[str, ...] = Field(default_factory=tuple)


class ProviderRecordV1(ImmutableContract):
    schema_version: str = "provider-record-v1"
    provider: str
    canonical_record_id: str
    source_record_id: str
    source_revision: str | None = None
    source_timestamp: str | None = None
    read_timestamp: str
    requested_fields: tuple[str, ...] = Field(default_factory=tuple)
    missing_fields: tuple[str, ...] = Field(default_factory=tuple)
    normalized_content: dict[str, Any] = Field(default_factory=dict)
    provenance: tuple[str, ...] = Field(default_factory=tuple)
    freshness: str = "operation_current"

    @property
    def normalized_content_digest(self) -> str:
        return _digest(self.normalized_content)


class OperationReadSnapshotV1(ImmutableContract):
    schema_version: str = "operation-read-snapshot-v1"
    operation_id: str
    correlation_id: str
    requested_scope: tuple[str, ...]
    authoritative_release_identity: str
    provider_records: tuple[ProviderRecordV1, ...]
    canonical_record_references: tuple[str, ...]
    source_revisions: tuple[str, ...]
    source_timestamps: tuple[str, ...]
    read_timestamps: tuple[str, ...]
    requested_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    pagination_complete: bool
    provenance: tuple[str, ...]
    freshness: str
    provider_read_receipts: tuple[ProviderReadReceiptV1, ...]
    contradictory_record_ids: tuple[str, ...] = Field(default_factory=tuple)
    snapshot_digest: str
    authoritative: bool = False
    reusable_across_operations: bool = False
    contains_authorization: bool = False
    contains_execution_intent: bool = False

    @model_validator(mode="after")
    def enforce_snapshot_boundary(self) -> OperationReadSnapshotV1:
        if self.authoritative or self.reusable_across_operations:
            raise ValueError("operation snapshots are non-authoritative and operation-bound")
        if self.contains_authorization or self.contains_execution_intent:
            raise ValueError("operation snapshots cannot contain authority or execution intent")
        return self


def build_operation_snapshot(
    *,
    operation_id: str,
    correlation_id: str,
    requested_scope: Iterable[str],
    authoritative_release_identity: str,
    provider_records: Iterable[ProviderRecordV1],
    provider_read_receipts: Iterable[ProviderReadReceiptV1],
    freshness: str = "operation_current",
) -> OperationReadSnapshotV1:
    """Build one deterministic immutable snapshot from normalized provider reads."""

    records = tuple(sorted(provider_records, key=lambda item: (item.provider, item.canonical_record_id)))
    receipts = tuple(sorted(provider_read_receipts, key=lambda item: (item.provider, item.request_id)))
    normalized_scope = tuple(sorted(set(requested_scope)))
    by_canonical: dict[str, set[str]] = defaultdict(set)
    for record in records:
        by_canonical[record.canonical_record_id].add(record.normalized_content_digest)
    contradictory = tuple(sorted(key for key, values in by_canonical.items() if len(values) > 1))
    payload = {
        "operation_id": operation_id,
        "correlation_id": correlation_id,
        "requested_scope": normalized_scope,
        "authoritative_release_identity": authoritative_release_identity,
        "provider_records": [record.model_dump(mode="json") for record in records],
        "provider_read_receipts": [receipt.model_dump(mode="json") for receipt in receipts],
        "freshness": freshness,
        "contradictory_record_ids": contradictory,
    }
    return OperationReadSnapshotV1(
        operation_id=operation_id,
        correlation_id=correlation_id,
        requested_scope=normalized_scope,
        authoritative_release_identity=authoritative_release_identity,
        provider_records=records,
        canonical_record_references=tuple(sorted({item.canonical_record_id for item in records})),
        source_revisions=tuple(sorted({item.source_revision for item in records if item.source_revision})),
        source_timestamps=tuple(sorted({item.source_timestamp for item in records if item.source_timestamp})),
        read_timestamps=tuple(sorted({item.read_timestamp for item in records})),
        requested_fields=tuple(sorted({field for item in records for field in item.requested_fields})),
        missing_fields=tuple(sorted({field for item in records for field in item.missing_fields})),
        pagination_complete=all(receipt.pagination_complete for receipt in receipts),
        provenance=tuple(sorted({entry for item in records for entry in item.provenance})),
        freshness=freshness,
        provider_read_receipts=receipts,
        contradictory_record_ids=contradictory,
        snapshot_digest=_digest(payload),
    )


class ReadRequirementV1(ImmutableContract):
    schema_version: str = "read-requirement-v1"
    requesting_capability: str
    provider: str
    record_type: str
    record_identities: tuple[str, ...] = Field(default_factory=tuple)
    required_fields: tuple[str, ...] = Field(default_factory=tuple)
    relationships_to_traverse: tuple[str, ...] = Field(default_factory=tuple)
    pagination_limit: int = Field(default=100, ge=1)
    batching_supported: bool = False
    conditional_revision: str | None = None
    evidence_required: bool = True


class OperationalReadPlanV1(ImmutableContract):
    schema_version: str = "operational-read-plan-v1"
    operation_id: str
    requesting_capabilities: tuple[str, ...]
    requested_record_types: tuple[str, ...]
    requested_record_identities: tuple[str, ...]
    required_fields: tuple[str, ...]
    relationships_to_traverse: tuple[str, ...]
    providers: tuple[str, ...]
    pagination_limits: dict[str, int]
    batching_opportunities: tuple[str, ...]
    duplicate_requests_removed: int = Field(ge=0)
    conditional_read_information: dict[str, str]
    expected_read_count: int = Field(ge=0)
    incomplete_requirements: tuple[str, ...] = Field(default_factory=tuple)
    plan_digest: str


def compile_read_plan(
    *, operation_id: str, requirements: Iterable[ReadRequirementV1]
) -> OperationalReadPlanV1:
    """Union and coalesce declared reads without deciding semantic necessity."""

    items = tuple(requirements)
    grouped: dict[tuple[str, str, tuple[str, ...]], list[ReadRequirementV1]] = defaultdict(list)
    for item in items:
        key = (item.provider, item.record_type, tuple(sorted(set(item.record_identities))))
        grouped[key].append(item)
    duplicate_count = sum(max(0, len(group) - 1) for group in grouped.values())
    expected_reads = len(grouped)
    pagination_limits: dict[str, int] = {}
    batching: list[str] = []
    conditional: dict[str, str] = {}
    incomplete: list[str] = []
    for (provider, record_type, identities), group in sorted(grouped.items()):
        plan_key = f"{provider}:{record_type}:{','.join(identities) or '*'}"
        pagination_limits[plan_key] = max(item.pagination_limit for item in group)
        if all(item.batching_supported for item in group) and identities:
            batching.append(plan_key)
        revisions = {item.conditional_revision for item in group if item.conditional_revision}
        if len(revisions) == 1:
            conditional[plan_key] = next(iter(revisions))
        elif len(revisions) > 1:
            incomplete.append(f"conflicting conditional revisions for {plan_key}")
    payload = {
        "operation_id": operation_id,
        "requirements": [item.model_dump(mode="json") for item in sorted(items, key=lambda x: x.digest())],
        "duplicate_requests_removed": duplicate_count,
        "expected_read_count": expected_reads,
        "pagination_limits": pagination_limits,
        "batching_opportunities": sorted(batching),
        "conditional_read_information": conditional,
        "incomplete_requirements": sorted(incomplete),
    }
    return OperationalReadPlanV1(
        operation_id=operation_id,
        requesting_capabilities=tuple(sorted({item.requesting_capability for item in items})),
        requested_record_types=tuple(sorted({item.record_type for item in items})),
        requested_record_identities=tuple(sorted({identity for item in items for identity in item.record_identities})),
        required_fields=tuple(sorted({field for item in items for field in item.required_fields})),
        relationships_to_traverse=tuple(
            sorted({relationship for item in items for relationship in item.relationships_to_traverse})
        ),
        providers=tuple(sorted({item.provider for item in items})),
        pagination_limits=pagination_limits,
        batching_opportunities=tuple(sorted(batching)),
        duplicate_requests_removed=duplicate_count,
        conditional_read_information=conditional,
        expected_read_count=expected_reads,
        incomplete_requirements=tuple(sorted(incomplete)),
        plan_digest=_digest(payload),
    )


class VerifiedRuntimeBundleV1(ImmutableContract):
    schema_version: str = "verified-runtime-bundle-v1"
    compiled_policy_registry: dict[str, str]
    validated_contract_registry: dict[str, str]
    validated_capability_registry: dict[str, str]
    validated_schemas: dict[str, str]
    command_to_capability_bindings: dict[str, str]
    capability_dependency_metadata: dict[str, tuple[str, ...]]
    architecture_identity: str
    source_commit: str
    package_version: str
    compiler_versions: dict[str, str]
    source_file_digests: dict[str, str]
    registry_digests: dict[str, str]
    bundle_digest: str
    authoritative: bool = False

    @model_validator(mode="after")
    def verify_bundle_digest(self) -> VerifiedRuntimeBundleV1:
        if self.authoritative:
            raise ValueError("verified runtime bundles are optimization artifacts, not authority")
        payload = self.model_dump(mode="json", exclude={"bundle_digest"})
        if _digest(payload) != self.bundle_digest:
            raise ValueError("verified runtime bundle digest mismatch")
        return self


class PerformanceBudgetV1(ImmutableContract):
    schema_version: str = "performance-budget-v1"
    release_version: str
    metric: str
    maximum: float = Field(gt=0)
    unit: str
    workload: str
    evidence_source: str
    correctness_gates_suppressible: bool = False

    @model_validator(mode="after")
    def protect_correctness(self) -> PerformanceBudgetV1:
        if self.correctness_gates_suppressible:
            raise ValueError("performance budgets cannot suppress correctness gates")
        return self


class ProviderReadMetricsV1(ImmutableContract):
    schema_version: str = "provider-read-metrics-v1"
    provider_round_trips: int = Field(ge=0)
    provider_bytes_read: int | None = Field(default=None, ge=0)
    records_requested: int = Field(ge=0)
    records_returned: int = Field(ge=0)
    duplicate_reads_eliminated: int = Field(ge=0)
    fabricated_measurements: bool = False

    @model_validator(mode="after")
    def reject_fabrication(self) -> ProviderReadMetricsV1:
        if self.fabricated_measurements:
            raise ValueError("provider performance measurements cannot be fabricated")
        return self


class RuntimeCompositionMetricsV1(ImmutableContract):
    schema_version: str = "runtime-composition-metrics-v1"
    full_components: int = Field(ge=0)
    composed_components: int = Field(ge=0)
    duration_ms: float = Field(ge=0)
    full_composition_duration_ms: float | None = Field(default=None, ge=0)
    broadened: bool = False


class PerformanceObservationV1(ImmutableContract):
    schema_version: str = "performance-observation-v1"
    operation_id: str
    release_identity: str
    workload: str
    initialization_duration_ms: float | None = Field(default=None, ge=0)
    bundle_load_duration_ms: float | None = Field(default=None, ge=0)
    source_compilation_duration_ms: float | None = Field(default=None, ge=0)
    snapshot_construction_duration_ms: float | None = Field(default=None, ge=0)
    full_recomputation_duration_ms: float | None = Field(default=None, ge=0)
    incremental_duration_ms: float | None = Field(default=None, ge=0)
    memory_bytes: int | None = Field(default=None, ge=0)
    provider_reads: ProviderReadMetricsV1 | None = None
    runtime_composition: RuntimeCompositionMetricsV1 | None = None
    telemetry_redacted: bool = True
    influences_authority_or_results: bool = False

    @model_validator(mode="after")
    def enforce_telemetry_boundary(self) -> PerformanceObservationV1:
        if not self.telemetry_redacted or self.influences_authority_or_results:
            raise ValueError("telemetry must be redacted and behavior-neutral")
        return self


class RuntimeDependencyDeclarationV1(ImmutableContract):
    schema_version: str = "runtime-dependency-declaration-v1"
    command: str
    capability: str
    contracts: tuple[str, ...] = Field(default_factory=tuple)
    policies: tuple[str, ...] = Field(default_factory=tuple)
    schemas: tuple[str, ...] = Field(default_factory=tuple)
    ports: tuple[str, ...] = Field(default_factory=tuple)
    adapters: tuple[str, ...] = Field(default_factory=tuple)
    consequential: bool = False
    broad_impact: bool = False
    complete: bool = True


class RuntimeCompositionPlanV1(ImmutableContract):
    schema_version: str = "runtime-composition-plan-v1"
    selected_command: str
    requested_capability: str
    required_capabilities: tuple[str, ...]
    required_contracts: tuple[str, ...]
    required_policies: tuple[str, ...]
    required_schemas: tuple[str, ...]
    required_ports: tuple[str, ...]
    required_adapters: tuple[str, ...]
    broadening_reasons: tuple[str, ...]
    full_composition_requirement: bool
    composition_digest: str


def compile_runtime_composition(
    *,
    command: str,
    declarations: Iterable[RuntimeDependencyDeclarationV1],
    force_full: bool = False,
) -> RuntimeCompositionPlanV1:
    """Compile the minimum declared runtime slice and broaden when uncertain."""

    matches = tuple(item for item in declarations if item.command == command)
    if not matches:
        raise ValueError(f"unknown command binding: {command}")
    reasons: list[str] = []
    full = force_full
    if any(not item.complete for item in matches):
        full = True
        reasons.append("incomplete dependency declaration")
    if any(item.consequential for item in matches):
        full = True
        reasons.append("consequential command")
    if any(item.broad_impact for item in matches):
        full = True
        reasons.append("policy-declared broad impact")
    payload = {
        "command": command,
        "declarations": [item.model_dump(mode="json") for item in sorted(matches, key=lambda x: x.digest())],
        "full": full,
        "reasons": sorted(set(reasons)),
    }
    return RuntimeCompositionPlanV1(
        selected_command=command,
        requested_capability=matches[0].capability,
        required_capabilities=tuple(sorted({item.capability for item in matches})),
        required_contracts=tuple(sorted({value for item in matches for value in item.contracts})),
        required_policies=tuple(sorted({value for item in matches for value in item.policies})),
        required_schemas=tuple(sorted({value for item in matches for value in item.schemas})),
        required_ports=tuple(sorted({value for item in matches for value in item.ports})),
        required_adapters=tuple(sorted({value for item in matches for value in item.adapters})),
        broadening_reasons=tuple(sorted(set(reasons))),
        full_composition_requirement=full,
        composition_digest=_digest(payload),
    )


class OperationalComputationNodeV1(ImmutableContract):
    schema_version: str = "operational-computation-node-v1"
    node_id: str
    canonical_record_id: str
    source_revision: str
    normalized_content_digest: str
    policy_digest: str
    contract_version: str
    capability_version: str
    dependency_digests: tuple[str, ...] = Field(default_factory=tuple)
    result_digest: str | None = None

    @property
    def computation_identity(self) -> str:
        return _digest(
            {
                "canonical_record_id": self.canonical_record_id,
                "source_revision": self.source_revision,
                "normalized_content_digest": self.normalized_content_digest,
                "policy_digest": self.policy_digest,
                "contract_version": self.contract_version,
                "capability_version": self.capability_version,
                "dependency_digests": sorted(self.dependency_digests),
            }
        )


class OperationalDependencyEdgeV1(ImmutableContract):
    schema_version: str = "operational-dependency-edge-v1"
    source_node_id: str
    dependent_node_id: str


class OperationalComputationGraphV1(ImmutableContract):
    schema_version: str = "operational-computation-graph-v1"
    nodes: tuple[OperationalComputationNodeV1, ...]
    edges: tuple[OperationalDependencyEdgeV1, ...]
    authority_identity: str
    schema_identity: str
    redaction_policy_digest: str
    complete: bool = True

    @model_validator(mode="after")
    def validate_edges(self) -> OperationalComputationGraphV1:
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.dependent_node_id not in node_ids:
                raise ValueError("operational graph edge references an unknown node")
        return self


class IncrementalComputationPlanV1(ImmutableContract):
    schema_version: str = "incremental-computation-plan-v1"
    changed_node_ids: tuple[str, ...]
    recompute_node_ids: tuple[str, ...]
    reusable_node_ids: tuple[str, ...]
    full_recomputation_required: bool
    fallback_reasons: tuple[str, ...]
    plan_digest: str


class IncrementalComputationReceiptV1(ImmutableContract):
    schema_version: str = "incremental-computation-receipt-v1"
    operation_id: str
    plan_digest: str
    evaluated_node_ids: tuple[str, ...]
    reused_node_ids: tuple[str, ...]
    full_recomputation_performed: bool
    equivalence_verified: bool
    persisted_index_authoritative: bool = False

    @model_validator(mode="after")
    def protect_index_boundary(self) -> IncrementalComputationReceiptV1:
        if self.persisted_index_authoritative:
            raise ValueError("incremental indexes and receipts are non-authoritative")
        return self


def plan_incremental_computation(
    *,
    current_graph: OperationalComputationGraphV1,
    prior_nodes: Iterable[OperationalComputationNodeV1],
    prior_authority_identity: str | None,
    prior_schema_identity: str | None,
    prior_redaction_policy_digest: str | None,
) -> IncrementalComputationPlanV1:
    """Plan sequential incremental recomputation with conservative fallback."""

    prior = {item.node_id: item for item in prior_nodes}
    reasons: list[str] = []
    full = not current_graph.complete
    if not current_graph.complete:
        reasons.append("incomplete dependency graph")
    if prior_authority_identity != current_graph.authority_identity:
        full = True
        reasons.append("authority identity changed")
    if prior_schema_identity != current_graph.schema_identity:
        full = True
        reasons.append("schema identity changed")
    if prior_redaction_policy_digest != current_graph.redaction_policy_digest:
        full = True
        reasons.append("redaction policy changed")

    changed = {
        node.node_id
        for node in current_graph.nodes
        if node.node_id not in prior
        or node.computation_identity != prior[node.node_id].computation_identity
    }
    dependents: dict[str, set[str]] = defaultdict(set)
    for edge in current_graph.edges:
        dependents[edge.source_node_id].add(edge.dependent_node_id)
    recompute = set(changed)
    queue: deque[str] = deque(sorted(changed))
    while queue:
        source = queue.popleft()
        for dependent in sorted(dependents[source]):
            if dependent not in recompute:
                recompute.add(dependent)
                queue.append(dependent)
    all_ids = {node.node_id for node in current_graph.nodes}
    if full:
        recompute = set(all_ids)
    reusable = all_ids - recompute
    payload = {
        "changed": sorted(changed),
        "recompute": sorted(recompute),
        "reusable": sorted(reusable),
        "full": full,
        "reasons": sorted(set(reasons)),
    }
    return IncrementalComputationPlanV1(
        changed_node_ids=tuple(sorted(changed)),
        recompute_node_ids=tuple(sorted(recompute)),
        reusable_node_ids=tuple(sorted(reusable)),
        full_recomputation_required=full,
        fallback_reasons=tuple(sorted(set(reasons))),
        plan_digest=_digest(payload),
    )
