from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from atlas_ros.intelligence.reasoning import ReasoningOutcome
from atlas_ros.intelligence.record_store import SQLiteIntelligenceRecordStore
from atlas_ros.intelligence.records import (
    ContextSnapshot,
    DecisionDisposition,
    DecisionGovernanceRecord,
    GovernancePolicyRecord,
    PolicyEvaluationOutcome,
    PolicyEvaluationRecord,
    RecommendationRecord,
    RecordRef,
)

MINIMUM_EVIDENCE_CONFIDENCE: Final = "minimum-evidence-confidence"
MINIMUM_AUTHORITY: Final = "minimum-authority"
CONTRADICTION_CHECK: Final = "contradiction-check"
REQUIRED_HUMAN_APPROVAL: Final = "required-human-approval"
MINIMUM_RECOMMENDATION_MARGIN: Final = "minimum-recommendation-margin"
MAXIMUM_UNSUPPORTED_ASSUMPTIONS: Final = "maximum-unsupported-assumptions"

_TRUE_VALUES: Final = frozenset({"1", "true", "yes", "granted", "approved"})
_FALSE_VALUES: Final = frozenset({"0", "false", "no", "denied", "not-granted"})


@dataclass(frozen=True)
class PolicyResult:
    """Deterministic result returned by one governance policy evaluator."""

    passed: bool
    reason: str
    confidence: float


@dataclass(frozen=True)
class GovernanceOutcome:
    """Complete governance result for one reasoning outcome."""

    evaluations: tuple[PolicyEvaluationRecord, ...]
    governance: DecisionGovernanceRecord


PolicyEvaluator = Callable[
    [GovernancePolicyRecord, ReasoningOutcome, ContextSnapshot],
    PolicyResult,
]


class GovernedDecisionEngine:
    """Evaluate persisted governance policies against a reasoning outcome."""

    def __init__(
        self,
        record_store: SQLiteIntelligenceRecordStore,
        *,
        evaluators: Mapping[str, PolicyEvaluator] | None = None,
    ) -> None:
        self.record_store = record_store
        self._evaluators: dict[str, PolicyEvaluator] = {
            MINIMUM_EVIDENCE_CONFIDENCE: self._minimum_evidence_confidence,
            MINIMUM_AUTHORITY: self._minimum_authority,
            CONTRADICTION_CHECK: self._contradiction_check,
            REQUIRED_HUMAN_APPROVAL: self._required_human_approval,
            MINIMUM_RECOMMENDATION_MARGIN: self._minimum_recommendation_margin,
            MAXIMUM_UNSUPPORTED_ASSUMPTIONS: (self._maximum_unsupported_assumptions),
        }

        if evaluators:
            self._evaluators.update(evaluators)

    def register_policy_evaluator(
        self,
        policy_key: str,
        evaluator: PolicyEvaluator,
        *,
        replace: bool = False,
    ) -> None:
        """Register an evaluator for a policy key."""

        normalized_key = policy_key.strip()
        if not normalized_key:
            raise ValueError("policy_key cannot be empty")

        if normalized_key in self._evaluators and not replace:
            raise ValueError(f"policy evaluator already registered: {normalized_key}")

        self._evaluators[normalized_key] = evaluator

    def evaluate(
        self,
        *,
        reasoning_outcome: ReasoningOutcome,
        context_ref: RecordRef,
        policy_refs: tuple[RecordRef, ...],
        created_at: datetime | None = None,
    ) -> GovernanceOutcome:
        """Evaluate active policies and produce an immutable governance record."""

        if not policy_refs:
            raise ValueError("at least one governance policy is required")

        if len(policy_refs) != len(set(policy_refs)):
            raise ValueError("governance policy references must be unique")

        context = self.record_store.resolve(context_ref)
        if not isinstance(context, ContextSnapshot):
            raise ValueError("context_ref must resolve to ContextSnapshot")

        timestamp = created_at or datetime.now(UTC)
        recommendation = reasoning_outcome.recommendation
        subject_ref = (
            recommendation.ref()
            if isinstance(recommendation, RecommendationRecord)
            else context.ref()
        )

        policies = tuple(self._resolve_policy(ref) for ref in policy_refs)
        active_policies = tuple(
            sorted(
                (policy for policy in policies if policy.active),
                key=lambda policy: (
                    policy.priority,
                    policy.policy_key,
                    str(policy.record_id),
                ),
            )
        )

        if not active_policies:
            raise ValueError("at least one active governance policy is required")

        evaluations = tuple(
            self._evaluate_policy(
                policy=policy,
                reasoning_outcome=reasoning_outcome,
                context=context,
                subject_ref=subject_ref,
                created_at=timestamp,
            )
            for policy in active_policies
        )

        disposition = self._select_disposition(
            reasoning_outcome=reasoning_outcome,
            evaluations=evaluations,
        )
        permitted = disposition is DecisionDisposition.ALLOW
        evidence_refs = self._evidence_refs(
            reasoning_outcome=reasoning_outcome,
            context=context,
        )
        recommendation_ref = (
            recommendation.ref() if isinstance(recommendation, RecommendationRecord) else None
        )

        governance = DecisionGovernanceRecord(
            created_at=timestamp,
            context_ref=context.ref(),
            recommendation_ref=recommendation_ref,
            policy_evaluation_refs=tuple(evaluation.ref() for evaluation in evaluations),
            disposition=disposition,
            permitted=permitted,
            explanation=self._build_explanation(
                reasoning_outcome=reasoning_outcome,
                evaluations=evaluations,
                disposition=disposition,
            ),
            evidence_refs=evidence_refs,
            links=tuple(
                dict.fromkeys(
                    (
                        context.ref(),
                        *((recommendation_ref,) if recommendation_ref is not None else ()),
                        *(evaluation.ref() for evaluation in evaluations),
                        *evidence_refs,
                    )
                )
            ),
        )

        return GovernanceOutcome(
            evaluations=evaluations,
            governance=governance,
        )

    def _resolve_policy(
        self,
        policy_ref: RecordRef,
    ) -> GovernancePolicyRecord:
        policy = self.record_store.resolve(policy_ref)

        if not isinstance(policy, GovernancePolicyRecord):
            raise ValueError("policy_refs must resolve to GovernancePolicyRecord")

        return policy

    def _evaluate_policy(
        self,
        *,
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
        subject_ref: RecordRef,
        created_at: datetime,
    ) -> PolicyEvaluationRecord:
        evaluator = self._evaluators.get(policy.policy_key)

        if evaluator is None:
            raise ValueError(f"unsupported governance policy: {policy.policy_key}")

        result = evaluator(
            policy,
            reasoning_outcome,
            context,
        )
        confidence = _bounded_probability(
            result.confidence,
            field_name="policy evaluation confidence",
        )

        outcome = PolicyEvaluationOutcome.PASS if result.passed else PolicyEvaluationOutcome.FAIL
        disposition = DecisionDisposition.ALLOW if result.passed else policy.failure_disposition
        evidence_refs = self._evidence_refs(
            reasoning_outcome=reasoning_outcome,
            context=context,
        )

        return PolicyEvaluationRecord(
            created_at=created_at,
            policy_ref=policy.ref(),
            subject_ref=subject_ref,
            outcome=outcome,
            disposition=disposition,
            reason=result.reason,
            evidence_refs=evidence_refs,
            confidence=confidence,
            links=tuple(
                dict.fromkeys(
                    (
                        policy.ref(),
                        subject_ref,
                        *evidence_refs,
                    )
                )
            ),
        )

    @staticmethod
    def _select_disposition(
        *,
        reasoning_outcome: ReasoningOutcome,
        evaluations: tuple[PolicyEvaluationRecord, ...],
    ) -> DecisionDisposition:
        if reasoning_outcome.trace.abstained or reasoning_outcome.recommendation is None:
            return DecisionDisposition.ABSTAIN

        failed = tuple(
            evaluation
            for evaluation in evaluations
            if evaluation.outcome is PolicyEvaluationOutcome.FAIL
        )

        if failed:
            return failed[0].disposition

        return DecisionDisposition.ALLOW

    @staticmethod
    def _build_explanation(
        *,
        reasoning_outcome: ReasoningOutcome,
        evaluations: tuple[PolicyEvaluationRecord, ...],
        disposition: DecisionDisposition,
    ) -> str:
        if reasoning_outcome.trace.abstained or reasoning_outcome.recommendation is None:
            return (
                "The reasoning engine issued no recommendation. Governance disposition is abstain."
            )

        failed = tuple(
            evaluation
            for evaluation in evaluations
            if evaluation.outcome is PolicyEvaluationOutcome.FAIL
        )

        if not failed:
            return (
                f"All {len(evaluations)} active governance policies passed. "
                "The recommendation is permitted."
            )

        failed_reasons = " ".join(evaluation.reason for evaluation in failed)
        return (
            f"{len(failed)} of {len(evaluations)} active governance policies "
            f"failed. Final disposition: {disposition.value}. "
            f"{failed_reasons}"
        )

    @staticmethod
    def _evidence_refs(
        *,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> tuple[RecordRef, ...]:
        recommendation = reasoning_outcome.recommendation
        recommendation_refs = (
            recommendation.evidence_refs if isinstance(recommendation, RecommendationRecord) else ()
        )
        assessed_refs = tuple(
            assessment.evidence_ref for assessment in reasoning_outcome.trace.evidence
        )

        return tuple(
            dict.fromkeys(
                (
                    *context.evidence_refs,
                    *recommendation_refs,
                    *assessed_refs,
                )
            )
        )

    @staticmethod
    def _minimum_evidence_confidence(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del context

        threshold = _float_parameter(
            policy,
            "minimum_confidence",
            default=0.70,
        )
        usable_evidence = tuple(
            assessment for assessment in reasoning_outcome.trace.evidence if assessment.usable
        )
        observed = (
            min(assessment.confidence for assessment in usable_evidence) if usable_evidence else 0.0
        )

        return PolicyResult(
            passed=observed >= threshold,
            reason=(
                f"Minimum usable evidence confidence was {observed:.3f}; "
                f"required minimum is {threshold:.3f}."
            ),
            confidence=observed,
        )

    @staticmethod
    def _minimum_authority(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del context

        threshold = _float_parameter(
            policy,
            "minimum_authority_score",
            default=0.75,
        )
        usable_evidence = tuple(
            assessment for assessment in reasoning_outcome.trace.evidence if assessment.usable
        )
        observed = (
            max(assessment.authority_score for assessment in usable_evidence)
            if usable_evidence
            else 0.0
        )

        return PolicyResult(
            passed=observed >= threshold,
            reason=(
                f"Strongest usable evidence authority score was "
                f"{observed:.3f}; required minimum is {threshold:.3f}."
            ),
            confidence=observed,
        )

    @staticmethod
    def _contradiction_check(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del policy, context

        unresolved_evidence = sum(
            conflict.resolved_by is None for conflict in reasoning_outcome.trace.conflicts
        )
        unresolved_claims = sum(
            conflict.resolved_by is None for conflict in reasoning_outcome.trace.claim_conflicts
        )
        unresolved_total = unresolved_evidence + unresolved_claims

        return PolicyResult(
            passed=unresolved_total == 0,
            reason=(f"Unresolved material contradictions: {unresolved_total}."),
            confidence=1.0 if unresolved_total == 0 else 0.0,
        )

    @staticmethod
    def _required_human_approval(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del reasoning_outcome

        required = _bool_parameter(
            policy,
            "required",
            default=True,
        )
        approval_value = context.user_state.get(
            "human_approval",
            context.environment.get("human_approval", ""),
        )
        approved = _parse_optional_bool(
            approval_value,
            field_name="human_approval",
        )

        if not required:
            return PolicyResult(
                passed=True,
                reason="Human approval is not required by this policy.",
                confidence=1.0,
            )

        return PolicyResult(
            passed=approved,
            reason=f"Required human approval granted: {approved}.",
            confidence=1.0 if approved else 0.0,
        )

    @staticmethod
    def _minimum_recommendation_margin(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del context

        threshold = _float_parameter(
            policy,
            "minimum_margin",
            default=0.05,
        )
        ranked_options = reasoning_outcome.trace.ranked_options
        margin = (
            ranked_options[0].adjusted_score - ranked_options[1].adjusted_score
            if len(ranked_options) >= 2
            else 0.0
        )

        return PolicyResult(
            passed=margin >= threshold,
            reason=(
                f"Recommendation margin was {margin:.3f}; required minimum is {threshold:.3f}."
            ),
            confidence=min(1.0, max(0.0, margin)),
        )

    @staticmethod
    def _maximum_unsupported_assumptions(
        policy: GovernancePolicyRecord,
        reasoning_outcome: ReasoningOutcome,
        context: ContextSnapshot,
    ) -> PolicyResult:
        del reasoning_outcome

        maximum = _int_parameter(
            policy,
            "maximum_count",
            default=0,
        )
        raw_count = context.environment.get(
            "unsupported_assumption_count",
            context.user_state.get(
                "unsupported_assumption_count",
                "0",
            ),
        )
        observed = _parse_non_negative_int(
            raw_count,
            field_name="unsupported_assumption_count",
        )
        passed = observed <= maximum

        if observed == 0:
            confidence = 1.0
        elif maximum == 0:
            confidence = 0.0
        else:
            confidence = max(
                0.0,
                1.0 - (observed / (maximum + 1)),
            )

        return PolicyResult(
            passed=passed,
            reason=(f"Unsupported assumptions: {observed}; maximum permitted is {maximum}."),
            confidence=confidence,
        )


def default_governance_policies(
    *,
    created_at: datetime | None = None,
) -> tuple[GovernancePolicyRecord, ...]:
    """Return the deterministic default governance policy set."""

    timestamp = created_at or datetime.now(UTC)

    return (
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=CONTRADICTION_CHECK,
            name="Contradiction check",
            description=(
                "Recommendations cannot proceed while material evidence "
                "or claim contradictions remain unresolved."
            ),
            failure_disposition=DecisionDisposition.ESCALATE,
            priority=10,
        ),
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=REQUIRED_HUMAN_APPROVAL,
            name="Required human approval",
            description=(
                "Consequential recommendations require explicit human approval before action."
            ),
            failure_disposition=DecisionDisposition.ESCALATE,
            priority=20,
            parameters={"required": False},
        ),
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=MINIMUM_EVIDENCE_CONFIDENCE,
            name="Minimum evidence confidence",
            description=("Recommendations require sufficiently confident usable evidence."),
            failure_disposition=DecisionDisposition.REQUEST_EVIDENCE,
            priority=30,
            parameters={"minimum_confidence": 0.70},
        ),
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=MINIMUM_AUTHORITY,
            name="Minimum authority",
            description=("Recommendations require usable evidence from an adequate authority."),
            failure_disposition=DecisionDisposition.REQUEST_EVIDENCE,
            priority=40,
            parameters={"minimum_authority_score": 0.75},
        ),
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=MINIMUM_RECOMMENDATION_MARGIN,
            name="Minimum recommendation margin",
            description=(
                "The leading recommendation must exceed competing options by a sufficient margin."
            ),
            failure_disposition=DecisionDisposition.ABSTAIN,
            priority=50,
            parameters={"minimum_margin": 0.05},
        ),
        GovernancePolicyRecord(
            created_at=timestamp,
            policy_key=MAXIMUM_UNSUPPORTED_ASSUMPTIONS,
            name="Maximum unsupported assumptions",
            description=(
                "Recommendations cannot rely on more unsupported assumptions than policy permits."
            ),
            failure_disposition=DecisionDisposition.REQUEST_CLARIFICATION,
            priority=60,
            parameters={"maximum_count": 0},
        ),
    )


def _float_parameter(
    policy: GovernancePolicyRecord,
    key: str,
    *,
    default: float,
) -> float:
    value = policy.parameters.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"policy parameter {key!r} must be numeric")

    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"policy parameter {key!r} must be between 0 and 1")

    return result


def _int_parameter(
    policy: GovernancePolicyRecord,
    key: str,
    *,
    default: int,
) -> int:
    value = policy.parameters.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"policy parameter {key!r} must be an integer")

    if value < 0:
        raise ValueError(f"policy parameter {key!r} cannot be negative")

    return value


def _bool_parameter(
    policy: GovernancePolicyRecord,
    key: str,
    *,
    default: bool,
) -> bool:
    value = policy.parameters.get(key, default)

    if not isinstance(value, bool):
        raise ValueError(f"policy parameter {key!r} must be boolean")

    return value


def _parse_optional_bool(
    value: str,
    *,
    field_name: str,
) -> bool:
    normalized = value.strip().lower()

    if not normalized:
        return False

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
        return False

    raise ValueError(f"context field {field_name!r} must contain a recognized boolean value")


def _parse_non_negative_int(
    value: str,
    *,
    field_name: str,
) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(f"context field {field_name!r} must contain an integer") from exc

    if result < 0:
        raise ValueError(f"context field {field_name!r} cannot be negative")

    return result


def _bounded_probability(
    value: float,
    *,
    field_name: str,
) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")

    return value
