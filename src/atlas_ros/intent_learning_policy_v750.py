from __future__ import annotations

from dataclasses import dataclass

from atlas_ros.engines.input_pipeline_v62 import AdaptiveInputProcessingPipelineV62
from atlas_ros.intent_learning_v750 import (
    ClarificationDecisionV1,
    ClarificationStatus,
    CompletionDimensionsV1,
    ConsequenceAssessmentV1,
    ContextFamiliarityV1,
    IntentEvidenceV1,
    RelatedRecordV1,
    decide_relationship,
)


@dataclass(frozen=True)
class AdaptiveClarificationPolicyV750:
    """Governed v7.5 policy wrapper around the existing v6.2 pipeline.

    This policy influences classification and clarification only. It cannot
    authorize execution, write providers, create Todoist objects, or replace
    the v6.2 fallback path.
    """

    enabled: bool = False

    def evaluate(
        self,
        *,
        capture: str,
        proposed_completion: CompletionDimensionsV1 | None,
        related_records: tuple[RelatedRecordV1, ...],
        familiarity: ContextFamiliarityV1,
        consequence: ConsequenceAssessmentV1,
        evidence: tuple[IntentEvidenceV1, ...] = (),
    ) -> ClarificationDecisionV1 | None:
        if not self.enabled:
            return None
        decision = decide_relationship(
            capture=capture,
            proposed_completion=proposed_completion,
            related_records=related_records,
            familiarity=familiarity,
            consequence=consequence,
            evidence=evidence,
        )
        if decision.provider_writes != 0 or decision.todoist_write_allowed:
            raise RuntimeError("v7.5 clarification policy violated execution boundary")
        return decision


class AdaptiveInputProcessingWithClarificationV750:
    """Attended composition of the existing v6.2 pipeline and v7.5 policy."""

    def __init__(
        self,
        *,
        base_pipeline: AdaptiveInputProcessingPipelineV62 | None = None,
        policy: AdaptiveClarificationPolicyV750 | None = None,
    ) -> None:
        self.base_pipeline = base_pipeline or AdaptiveInputProcessingPipelineV62()
        self.policy = policy or AdaptiveClarificationPolicyV750(enabled=False)

    def process(self, raw_input: str, **kwargs: object) -> object:
        return self.base_pipeline.process(raw_input, **kwargs)

    def evaluate_clarification(self, **kwargs: object) -> ClarificationDecisionV1 | None:
        return self.policy.evaluate(**kwargs)  # type: ignore[arg-type]

    @staticmethod
    def execution_blocked(decision: ClarificationDecisionV1 | None) -> bool:
        return bool(
            decision
            and decision.clarification_status == ClarificationStatus.REQUIRED
        )
