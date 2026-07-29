"""Disabled-by-default feature policy for governed intent memory."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from atlas_ros.intent_memory_v760 import (
    EligibilityStatus,
    FeatureMode,
    GovernedIntentEvidenceV1,
    IntentContextKeyV1,
    IntentEligibilityDecisionV1,
    IntentFreshnessPolicyV1,
    IntentInspectionViewV1,
    decide_intent_eligibility,
    inspect_intent_evidence,
)


@dataclass(frozen=True)
class IntentMemoryFeaturePolicyV760:
    mode: FeatureMode = FeatureMode.DISABLED
    disabled_scope_digests: frozenset[str] = frozenset()
    disabled_evidence_ids: frozenset[str] = frozenset()

    @property
    def inspection_enabled(self) -> bool:
        return self.mode in (FeatureMode.INSPECTION, FeatureMode.INFERENCE)

    @property
    def inference_enabled(self) -> bool:
        return self.mode is FeatureMode.INFERENCE

    def evaluate(
        self,
        *,
        evidence: GovernedIntentEvidenceV1,
        request_context: IntentContextKeyV1,
        freshness_policy: IntentFreshnessPolicyV1,
        now: str,
        consequential: bool = False,
        current_instruction_present: bool = False,
        live_authority_present: bool = False,
    ) -> IntentEligibilityDecisionV1:
        return decide_intent_eligibility(
            evidence=evidence,
            request_context=request_context,
            policy=freshness_policy,
            feature_mode=self.mode,
            now=now,
            consequential=consequential,
            current_instruction_present=current_instruction_present,
            live_authority_present=live_authority_present,
            scope_disabled=(
                request_context.scope.deterministic_digest
                in self.disabled_scope_digests
            ),
            evidence_disabled=evidence.evidence_id in self.disabled_evidence_ids,
        )

    def inspect(
        self,
        *,
        evidence: GovernedIntentEvidenceV1,
        decision: IntentEligibilityDecisionV1,
    ) -> IntentInspectionViewV1 | None:
        if not self.inspection_enabled:
            return None
        return inspect_intent_evidence(evidence, decision)

    def resolve_or_fallback[T](
        self,
        *,
        decision: IntentEligibilityDecisionV1,
        inferred: Callable[[], T],
        predecessor: Callable[[], T],
    ) -> T:
        if self.inference_enabled and decision.status is EligibilityStatus.ELIGIBLE:
            return inferred()
        return predecessor()
