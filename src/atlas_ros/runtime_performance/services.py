"""Sequential runtime-performance services with fail-safe fallbacks.

These services remain provider-neutral and authority-neutral. They do not authorize
writes, retain credentials, introduce concurrency, or replace canonical source
compilation and full recomputation paths.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from atlas_ros.runtime_performance.contracts import (
    IncrementalComputationPlanV1,
    OperationalComputationGraphV1,
    OperationalComputationNodeV1,
    OperationalReadPlanV1,
    OperationReadSnapshotV1,
    ProviderReadReceiptV1,
    ProviderRecordV1,
    ReadRequirementV1,
    RuntimeCompositionPlanV1,
    RuntimeDependencyDeclarationV1,
    VerifiedRuntimeBundleV1,
    _digest,
    build_operation_snapshot,
    compile_read_plan,
    compile_runtime_composition,
    plan_incremental_computation,
)


class SequentialReadAdapter(Protocol):
    """Translate one provider-neutral plan into sequential provider reads."""

    def execute_read_plan(
        self, plan: OperationalReadPlanV1
    ) -> tuple[tuple[ProviderRecordV1, ...], tuple[ProviderReadReceiptV1, ...]]: ...


@dataclass(frozen=True)
class OperationSnapshotCoordinator:
    """Compile one read plan and create one immutable operation snapshot."""

    authoritative_release_identity: str

    def execute(
        self,
        *,
        operation_id: str,
        correlation_id: str,
        requested_scope: Iterable[str],
        requirements: Iterable[ReadRequirementV1],
        adapters: Mapping[str, SequentialReadAdapter],
    ) -> tuple[OperationalReadPlanV1, OperationReadSnapshotV1]:
        plan = compile_read_plan(operation_id=operation_id, requirements=requirements)
        records: list[ProviderRecordV1] = []
        receipts: list[ProviderReadReceiptV1] = []
        for provider in plan.providers:
            adapter = adapters.get(provider)
            if adapter is None:
                raise ValueError(f"missing read adapter for provider: {provider}")
            provider_records, provider_receipts = adapter.execute_read_plan(plan)
            records.extend(provider_records)
            receipts.extend(provider_receipts)
        snapshot = build_operation_snapshot(
            operation_id=operation_id,
            correlation_id=correlation_id,
            requested_scope=requested_scope,
            authoritative_release_identity=self.authoritative_release_identity,
            provider_records=records,
            provider_read_receipts=receipts,
        )
        if plan.incomplete_requirements or not snapshot.pagination_complete:
            raise ValueError("operation read evidence is incomplete")
        return plan, snapshot


@dataclass(frozen=True)
class RuntimeBundleBuilder:
    """Build a deterministic optimization bundle from verified registries."""

    architecture_identity: str
    source_commit: str
    package_version: str
    compiler_versions: Mapping[str, str]

    def build(
        self,
        *,
        policies: Mapping[str, str],
        contracts: Mapping[str, str],
        capabilities: Mapping[str, str],
        schemas: Mapping[str, str],
        command_bindings: Mapping[str, str],
        dependencies: Mapping[str, tuple[str, ...]],
        source_file_digests: Mapping[str, str],
    ) -> VerifiedRuntimeBundleV1:
        registry_digests = {
            "policies": _digest(dict(sorted(policies.items()))),
            "contracts": _digest(dict(sorted(contracts.items()))),
            "capabilities": _digest(dict(sorted(capabilities.items()))),
            "schemas": _digest(dict(sorted(schemas.items()))),
            "commands": _digest(dict(sorted(command_bindings.items()))),
            "dependencies": _digest(
                {key: sorted(value) for key, value in sorted(dependencies.items())}
            ),
        }
        payload: dict[str, Any] = {
            "schema_version": "verified-runtime-bundle-v1",
            "compiled_policy_registry": dict(sorted(policies.items())),
            "validated_contract_registry": dict(sorted(contracts.items())),
            "validated_capability_registry": dict(sorted(capabilities.items())),
            "validated_schemas": dict(sorted(schemas.items())),
            "command_to_capability_bindings": dict(sorted(command_bindings.items())),
            "capability_dependency_metadata": {
                key: tuple(sorted(value)) for key, value in sorted(dependencies.items())
            },
            "architecture_identity": self.architecture_identity,
            "source_commit": self.source_commit,
            "package_version": self.package_version,
            "compiler_versions": dict(sorted(self.compiler_versions.items())),
            "source_file_digests": dict(sorted(source_file_digests.items())),
            "registry_digests": registry_digests,
            "authoritative": False,
        }
        return VerifiedRuntimeBundleV1(**payload, bundle_digest=_digest(payload))


@dataclass(frozen=True)
class RuntimeBundleVerifier:
    """Verify bundle identity or execute canonical source compilation fallback."""

    expected_source_commit: str
    expected_package_version: str
    expected_architecture_identity: str

    def load_or_compile(
        self,
        *,
        bundle: VerifiedRuntimeBundleV1 | None,
        source_compiler: Callable[[], VerifiedRuntimeBundleV1],
    ) -> tuple[VerifiedRuntimeBundleV1, str]:
        if bundle is not None and self._valid_identity(bundle):
            return bundle, "verified_bundle"
        compiled = source_compiler()
        if not self._valid_identity(compiled):
            raise ValueError("bundle and canonical source compilation are invalid")
        return compiled, "canonical_source_fallback"

    def _valid_identity(self, bundle: VerifiedRuntimeBundleV1) -> bool:
        return (
            bundle.source_commit == self.expected_source_commit
            and bundle.package_version == self.expected_package_version
            and bundle.architecture_identity == self.expected_architecture_identity
        )


@dataclass(frozen=True)
class CapabilityScopedComposer:
    """Compile scoped composition with conservative full fallback."""

    declarations: tuple[RuntimeDependencyDeclarationV1, ...]

    def compose(self, command: str, *, force_full: bool = False) -> RuntimeCompositionPlanV1:
        return compile_runtime_composition(
            command=command,
            declarations=self.declarations,
            force_full=force_full,
        )

    def verify_equivalence(self, command: str) -> bool:
        scoped = self.compose(command)
        full = self.compose(command, force_full=True)
        return (
            scoped.required_capabilities == full.required_capabilities
            and scoped.required_contracts == full.required_contracts
            and scoped.required_policies == full.required_policies
            and scoped.required_schemas == full.required_schemas
            and scoped.required_ports == full.required_ports
            and scoped.required_adapters == full.required_adapters
        )


@dataclass(frozen=True)
class NonAuthoritativeIncrementalIndex:
    """Disposable digest-bound index that can always be rebuilt."""

    authority_identity: str
    schema_identity: str
    redaction_policy_digest: str
    nodes: tuple[OperationalComputationNodeV1, ...]
    authoritative: bool = False

    def __post_init__(self) -> None:
        if self.authoritative:
            raise ValueError("incremental indexes cannot be authoritative")


@dataclass(frozen=True)
class IncrementalOperationalPlanner:
    """Plan affected-node recomputation with full fallback when uncertain."""

    def plan(
        self,
        *,
        current_graph: OperationalComputationGraphV1,
        prior_index: NonAuthoritativeIncrementalIndex | None,
    ) -> IncrementalComputationPlanV1:
        if prior_index is None:
            return plan_incremental_computation(
                current_graph=current_graph.model_copy(update={"complete": False}),
                prior_nodes=(),
                prior_authority_identity=None,
                prior_schema_identity=None,
                prior_redaction_policy_digest=None,
            )
        return plan_incremental_computation(
            current_graph=current_graph,
            prior_nodes=prior_index.nodes,
            prior_authority_identity=prior_index.authority_identity,
            prior_schema_identity=prior_index.schema_identity,
            prior_redaction_policy_digest=prior_index.redaction_policy_digest,
        )
