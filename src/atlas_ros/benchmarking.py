from __future__ import annotations

from atlas_ros.contracts.coherence_v1 import BenchmarkExecutionPolicyV1, BenchmarkMode
from atlas_ros.contracts.models import deterministic_digest


class BenchmarkLifecyclePolicy:
    """Constructs validated benchmark policies without performing provider writes."""

    @staticmethod
    def provider_free() -> BenchmarkExecutionPolicyV1:
        return BenchmarkLifecyclePolicy._build(
            mode=BenchmarkMode.PROVIDER_FREE_SEMANTIC,
            provider_writes_allowed=False,
            exact_object_budget=0,
            explicit_authorization_required=False,
            provider_readback_required=False,
            reconciliation_required=False,
            record_strategy="review_record",
        )

    @staticmethod
    def shadow() -> BenchmarkExecutionPolicyV1:
        return BenchmarkLifecyclePolicy._build(
            mode=BenchmarkMode.SHADOW_ORCHESTRATION,
            provider_writes_allowed=False,
            exact_object_budget=0,
            explicit_authorization_required=False,
            provider_readback_required=False,
            reconciliation_required=False,
            record_strategy="review_record",
        )

    @staticmethod
    def attended_canary(
        *,
        exact_object_budget: int,
        explicitly_authorized: bool,
    ) -> BenchmarkExecutionPolicyV1:
        if not explicitly_authorized:
            raise ValueError("attended provider canary requires explicit authorization")
        return BenchmarkLifecyclePolicy._build(
            mode=BenchmarkMode.ATTENDED_PROVIDER_CANARY,
            provider_writes_allowed=True,
            exact_object_budget=exact_object_budget,
            explicit_authorization_required=True,
            provider_readback_required=True,
            reconciliation_required=True,
            record_strategy="operational_record",
        )

    @staticmethod
    def default() -> BenchmarkExecutionPolicyV1:
        return BenchmarkLifecyclePolicy.provider_free()

    @staticmethod
    def _build(**values: object) -> BenchmarkExecutionPolicyV1:
        unsigned = BenchmarkExecutionPolicyV1(policy_digest="0" * 64, **values)
        return BenchmarkExecutionPolicyV1(
            **values,
            policy_digest=deterministic_digest(unsigned.digest_payload()),
        )
