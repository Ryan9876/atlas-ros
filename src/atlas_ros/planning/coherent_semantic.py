from __future__ import annotations

from atlas_ros.contracts import (
    ExecutionCandidateV3,
    ManagementPackageV3,
    SemanticConditionResult,
    SemanticFidelityResultV1,
    deterministic_digest,
)
from atlas_ros.planning.semantic import SemanticExecutionPlanner as BaseSemanticExecutionPlanner


class SemanticExecutionPlanner(BaseSemanticExecutionPlanner):
    """Semantic planner that makes reasoning coherence release-blocking."""

    def _evaluate(
        self,
        management: ManagementPackageV3,
        parent: ExecutionCandidateV3,
        current: tuple[ExecutionCandidateV3, ...],
    ) -> SemanticFidelityResultV1:
        base = super()._evaluate(management, parent, current)
        coherence_passed = (
            management.reasoning_coherence is not None
            and management.reasoning_coherence.passed
            and not management.reasoning_coherence.review_required
            and management.reasoning_coherence.verify_digest()
        )
        coherence = SemanticConditionResult(
            condition="reasoning_coherence",
            passed=coherence_passed,
            reason_code=(
                "reasoning_coherence_required_passed"
                if coherence_passed
                else "reasoning_coherence_required_failed"
            ),
            detail=(
                "Reasoning metadata, confidence, routing, review state, and explanation "
                "must describe one governed conclusion."
            ),
        )
        conditions = (*base.conditions, coherence)
        fingerprint = deterministic_digest(
            {
                "business_plan": base.business_plan_fingerprint,
                "planning_model": management.planning_model_id,
                "responsibility": management.responsibility,
                "workstream": management.workstream,
                "review_required": (
                    management.reasoning_coherence.review_required
                    if management.reasoning_coherence is not None
                    else True
                ),
                "reasoning_summary": management.user_facing_summary,
            }
        )
        passed = all(condition.passed for condition in conditions)
        unsigned = SemanticFidelityResultV1(
            primary_outcome_reference=base.primary_outcome_reference,
            conditions=conditions,
            passed=passed,
            review_required=not passed,
            business_plan_fingerprint=fingerprint,
            result_digest="0" * 64,
        )
        return SemanticFidelityResultV1(
            primary_outcome_reference=base.primary_outcome_reference,
            conditions=conditions,
            passed=passed,
            review_required=not passed,
            business_plan_fingerprint=fingerprint,
            result_digest=deterministic_digest(unsigned.digest_payload()),
        )
