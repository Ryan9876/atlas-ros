"""Provider-free v6.5 governed execution intelligence.

The module is pure and advisory: it cannot call providers, create work, authorize
execution, schedule, send messages, or mutate live system state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from json import dumps
from math import isfinite
from re import sub
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence


def _digest(value: object) -> str:
    return sha256(
        dumps(value, default=str, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _safe_text(value: str) -> str:
    value = sub(r"[\x00-\x1f<>]", "", value)
    value = sub(
        r"(?i)(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+",
        "[REDACTED]",
        value,
    )
    return value.strip()


class AdvisoryError(ValueError):
    """A fail-closed v6.5 advisory validation error."""


class AuthorityTier(StrEnum):
    ORGANIZATION_POLICY = "organization_policy"
    RELEASE_CONTROL = "release_control"
    APPROVED_STANDARD = "approved_standard"
    PREFERENCE = "preference"


class ClaimStateV65(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    PROPOSAL = "proposal"
    APPROVAL = "approval"
    ACTION = "action"


class ExecutionStateV65(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PARTIAL_FAILURE = "partial_failure"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


_TIER_ORDER: Mapping[AuthorityTier, int] = {
    AuthorityTier.ORGANIZATION_POLICY: 0,
    AuthorityTier.RELEASE_CONTROL: 1,
    AuthorityTier.APPROVED_STANDARD: 2,
    AuthorityTier.PREFERENCE: 3,
}
_ALLOWED: Mapping[ExecutionStateV65, frozenset[ExecutionStateV65]] = {
    ExecutionStateV65.PENDING: frozenset(
        {ExecutionStateV65.READY, ExecutionStateV65.BLOCKED}
    ),
    ExecutionStateV65.READY: frozenset(
        {ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.BLOCKED}
    ),
    ExecutionStateV65.IN_PROGRESS: frozenset(
        {
            ExecutionStateV65.SUCCEEDED,
            ExecutionStateV65.PARTIAL_FAILURE,
            ExecutionStateV65.FAILED,
            ExecutionStateV65.BLOCKED,
        }
    ),
    ExecutionStateV65.PARTIAL_FAILURE: frozenset(
        {ExecutionStateV65.READY, ExecutionStateV65.BLOCKED, ExecutionStateV65.FAILED}
    ),
    ExecutionStateV65.BLOCKED: frozenset({ExecutionStateV65.READY, ExecutionStateV65.FAILED}),
    ExecutionStateV65.SUCCEEDED: frozenset(),
    ExecutionStateV65.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class FrameworkRuleV65:
    rule_id: str
    requirement: str
    tier: AuthorityTier
    source_version: str
    source_ref: str
    immutable: bool = False
    effective: bool = True
    requires: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            item.strip()
            for item in (self.rule_id, self.requirement, self.source_version, self.source_ref)
        ):
            raise AdvisoryError("framework_rule_requires_governed_provenance")
        if self.rule_id in self.requires:
            raise AdvisoryError("cyclic_framework_dependency")


@dataclass(frozen=True, slots=True)
class FrameworkCompositionV65:
    rules: tuple[FrameworkRuleV65, ...]
    warnings: tuple[str, ...]
    digest: str
    provenance: tuple[str, ...]


class GovernedFrameworkComposerV65:
    """Compose governed requirements without silently weakening higher authority."""

    def compose(self, rules: Sequence[FrameworkRuleV65]) -> FrameworkCompositionV65:
        by_id: dict[str, list[FrameworkRuleV65]] = {}
        for rule in rules:
            by_id.setdefault(rule.rule_id, []).append(rule)
        self._validate_dependencies(by_id)
        selected: list[FrameworkRuleV65] = []
        warnings: list[str] = []
        for rule_id in sorted(by_id):
            candidates = sorted(
                (rule for rule in by_id[rule_id] if rule.effective),
                key=lambda rule: (_TIER_ORDER[rule.tier], rule.source_version, rule.source_ref),
            )
            if not candidates:
                warnings.append(f"stale_or_inactive:{rule_id}")
                continue
            requirements = {rule.requirement for rule in candidates}
            if len(requirements) > 1:
                raise AdvisoryError(f"conflicting_rule:{rule_id}")
            winner = candidates[0]
            selected.append(winner)
            if any(
                _TIER_ORDER[candidate.tier] > _TIER_ORDER[winner.tier]
                for candidate in candidates[1:]
            ):
                warnings.append(f"lower_authority_ignored:{rule_id}")
            if winner.tier is AuthorityTier.PREFERENCE and winner.immutable:
                raise AdvisoryError(f"immutable_preference_not_governed:{rule_id}")
        ordered = tuple(
            sorted(selected, key=lambda rule: (_TIER_ORDER[rule.tier], rule.rule_id))
        )
        provenance = tuple(
            f"{rule.rule_id}@{rule.source_version}:{rule.source_ref}" for rule in ordered
        )
        payload = [
            (
                rule.rule_id,
                rule.requirement,
                rule.tier.value,
                rule.source_version,
                rule.source_ref,
                rule.immutable,
                rule.requires,
            )
            for rule in ordered
        ]
        return FrameworkCompositionV65(
            rules=ordered,
            warnings=tuple(sorted(warnings)),
            digest=_digest(payload),
            provenance=provenance,
        )

    @staticmethod
    def _validate_dependencies(by_id: Mapping[str, Sequence[FrameworkRuleV65]]) -> None:
        dependencies = {
            rule_id: {
                required
                for rule in alternatives
                for required in rule.requires
                if required in by_id
            }
            for rule_id, alternatives in by_id.items()
        }
        missing = sorted(
            required
            for alternatives in by_id.values()
            for rule in alternatives
            for required in rule.requires
            if required not in by_id
        )
        if missing:
            raise AdvisoryError(f"missing_framework_dependency:{missing[0]}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(rule_id: str) -> None:
            if rule_id in visiting:
                raise AdvisoryError("cyclic_framework_dependencies")
            if rule_id in visited:
                return
            visiting.add(rule_id)
            for required in sorted(dependencies[rule_id]):
                visit(required)
            visiting.remove(rule_id)
            visited.add(rule_id)

        for rule_id in sorted(dependencies):
            visit(rule_id)


@dataclass(frozen=True, slots=True)
class PathStepV65:
    step_id: str
    title: str
    prerequisites: tuple[str, ...] = ()
    mandatory: bool = False
    gate: str | None = None
    evidence_required: tuple[str, ...] = ()
    rollback: str | None = None
    risk: str = "unknown"
    reversibility: str = "unknown"
    cost: str = "unknown"
    side_effect: bool = False
    availability_impact: str = "unknown"
    escalation: str | None = None

    def __post_init__(self) -> None:
        if not self.step_id.strip() or not self.title.strip():
            raise AdvisoryError("path_step_requires_identifier_and_title")
        if self.step_id in self.prerequisites:
            raise AdvisoryError("cyclic_path_prerequisites")
        if self.gate is not None and not self.gate.strip():
            raise AdvisoryError("empty_path_gate")
        if self.side_effect and not self.rollback:
            raise AdvisoryError("side_effect_requires_rollback")


@dataclass(frozen=True, slots=True)
class MinimumEffectivePathV65:
    steps: tuple[PathStepV65, ...]
    blockers: tuple[str, ...]
    digest: str
    required_evidence: tuple[str, ...]
    escalations: tuple[str, ...]


class MinimumEffectivePathPlannerV65:
    """Produce a deterministic, qualified path without dropping mandatory controls."""

    def plan(self, steps: Sequence[PathStepV65], targets: Iterable[str]) -> MinimumEffectivePathV65:
        index = {step.step_id: step for step in steps}
        if len(index) != len(steps):
            raise AdvisoryError("duplicate_path_step")
        required = set(targets) | {step.step_id for step in steps if step.mandatory}
        if not required:
            raise AdvisoryError("minimum_path_requires_target_or_mandatory_control")
        pending = list(required)
        while pending:
            step_id = pending.pop()
            step = index.get(step_id)
            if step is None:
                raise AdvisoryError(f"missing_prerequisite:{step_id}")
            for prerequisite in step.prerequisites:
                if prerequisite not in index:
                    raise AdvisoryError(f"missing_prerequisite:{prerequisite}")
                if prerequisite not in required:
                    required.add(prerequisite)
                    pending.append(prerequisite)
        ordered = self._topological_order(index, required)
        blockers = tuple(
            f"unknown:{step.step_id}:{field_name}"
            for step in ordered
            for field_name, value in (
                ("risk", step.risk),
                ("reversibility", step.reversibility),
                ("cost", step.cost),
                ("availability_impact", step.availability_impact),
            )
            if value == "unknown"
        )
        evidence = tuple(sorted({item for step in ordered for item in step.evidence_required}))
        escalations = tuple(
            f"{step.step_id}:{step.escalation}"
            for step in ordered
            if step.escalation is not None
        )
        payload = [
            (
                step.step_id,
                step.prerequisites,
                step.mandatory,
                step.gate,
                step.evidence_required,
                step.rollback,
                step.risk,
                step.reversibility,
                step.cost,
                step.side_effect,
                step.availability_impact,
                step.escalation,
            )
            for step in ordered
        ]
        return MinimumEffectivePathV65(
            steps=tuple(ordered),
            blockers=blockers,
            digest=_digest(payload),
            required_evidence=evidence,
            escalations=escalations,
        )

    @staticmethod
    def _topological_order(
        index: Mapping[str, PathStepV65], required: set[str]
    ) -> list[PathStepV65]:
        remaining = set(required)
        ordered: list[PathStepV65] = []
        while remaining:
            eligible = sorted(
                step_id
                for step_id in remaining
                if set(index[step_id].prerequisites).isdisjoint(remaining)
            )
            if not eligible:
                raise AdvisoryError("cyclic_path_prerequisites")
            for step_id in eligible:
                ordered.append(index[step_id])
                remaining.remove(step_id)
        return ordered


@dataclass(frozen=True, slots=True)
class ExecutionEventV65:
    event_id: str
    from_state: ExecutionStateV65
    to_state: ExecutionStateV65
    evidence_refs: tuple[str, ...] = ()
    idempotency_key: str = ""
    detail: str = ""
    readback_refs: tuple[str, ...] = ()
    retry_of: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise AdvisoryError("execution_event_requires_identifier")
        if self.to_state is ExecutionStateV65.SUCCEEDED and not self.evidence_refs:
            raise AdvisoryError("completion_requires_evidence")
        if self.retry_of is not None and not self.retry_of.strip():
            raise AdvisoryError("invalid_retry_reference")


@dataclass(frozen=True, slots=True)
class ExecutionRecordV65:
    record_id: str
    state: ExecutionStateV65 = ExecutionStateV65.PENDING
    events: tuple[ExecutionEventV65, ...] = ()
    receipts: tuple[str, ...] = ()
    provider_writes: int = 0
    authority_create: bool = False
    authority_update: bool = False
    authority_delete: bool = False
    authority_schedule: bool = False
    authority_send_message: bool = False
    authority_authorize: bool = False
    authority_execute: bool = False

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise AdvisoryError("execution_record_requires_identifier")
        if self.provider_writes or any(
            (
                self.authority_create,
                self.authority_update,
                self.authority_delete,
                self.authority_schedule,
                self.authority_send_message,
                self.authority_authorize,
                self.authority_execute,
            )
        ):
            raise AdvisoryError("execution_intelligence_must_remain_provider_free")

    def transition(self, event: ExecutionEventV65) -> ExecutionRecordV65:
        same_key = next(
            (item for item in self.events if event.idempotency_key and item.idempotency_key == event.idempotency_key),
            None,
        )
        if same_key is not None:
            if same_key != event:
                raise AdvisoryError("idempotency_key_reused_with_different_event")
            return self
        if event.event_id in {item.event_id for item in self.events}:
            raise AdvisoryError("duplicate_execution_event")
        if event.from_state is not self.state or event.to_state not in _ALLOWED[self.state]:
            raise AdvisoryError("invalid_execution_transition")
        if event.retry_of is not None and not any(
            item.event_id == event.retry_of and item.to_state is ExecutionStateV65.PARTIAL_FAILURE
            for item in self.events
        ):
            raise AdvisoryError("retry_requires_partial_failure_reference")
        if event.to_state is ExecutionStateV65.SUCCEEDED and not event.readback_refs:
            raise AdvisoryError("completion_requires_readback")
        receipts = tuple(sorted(set(self.receipts) | set(event.evidence_refs) | set(event.readback_refs)))
        return ExecutionRecordV65(
            record_id=self.record_id,
            state=event.to_state,
            events=self.events + (event,),
            receipts=receipts,
        )

    def next_valid_actions(self) -> tuple[ExecutionStateV65, ...]:
        return tuple(sorted(_ALLOWED[self.state], key=lambda value: value.value))

    def audit_digest(self) -> str:
        return _digest(
            {
                "record_id": self.record_id,
                "state": self.state.value,
                "events": [
                    (
                        item.event_id,
                        item.from_state.value,
                        item.to_state.value,
                        item.evidence_refs,
                        item.idempotency_key,
                        _safe_text(item.detail),
                        item.readback_refs,
                        item.retry_of,
                    )
                    for item in self.events
                ],
                "receipts": self.receipts,
            }
        )

    @classmethod
    def replay(cls, record_id: str, events: Sequence[ExecutionEventV65]) -> ExecutionRecordV65:
        record = cls(record_id=record_id)
        for event in events:
            record = record.transition(event)
        return record


@dataclass(frozen=True, slots=True)
class PresentationEntryV65:
    state: ClaimStateV65
    text: str
    audit_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PresentationV65:
    executive: str
    technical: str
    audit_digest: str
    plain_text: str = ""


class ExecutionPresenterV65:
    """Render safe, evidence-labelled views without asserting unverified completion."""

    def render(
        self,
        *,
        facts: Sequence[str],
        actions: Sequence[str],
        warnings: Sequence[str],
        blockers: Sequence[str],
        assumptions: Sequence[str],
        next_steps: Sequence[str],
        audit_refs: Sequence[str],
        decisions: Sequence[str] = (),
        stale: Sequence[str] = (),
        conflicts: Sequence[str] = (),
    ) -> PresentationV65:
        entries = (
            tuple(PresentationEntryV65(ClaimStateV65.FACT, item) for item in facts)
            + tuple(PresentationEntryV65(ClaimStateV65.ACTION, item) for item in actions)
            + tuple(PresentationEntryV65(ClaimStateV65.PROPOSAL, item) for item in next_steps)
            + tuple(PresentationEntryV65(ClaimStateV65.APPROVAL, item) for item in decisions)
        )
        sections = (
            ("Verified facts", facts),
            ("Actions", actions),
            ("Warnings", warnings),
            ("Blockers", blockers),
            ("Assumptions", assumptions),
            ("Decisions", decisions),
            ("Stale state", stale),
            ("Conflicts", conflicts),
            ("Next steps", next_steps),
            ("Audit references", audit_refs),
        )
        markdown = "\n\n".join(
            f"## {name}\n"
            + ("\n".join(f"- {_safe_text(value)}" for value in values) if values else "- None")
            for name, values in sections
        )
        plain_text = sub(r"^## ", "", markdown, flags=0)
        digest = _digest(
            {
                "entries": [
                    (entry.state.value, _safe_text(entry.text), entry.audit_ref) for entry in entries
                ],
                "warnings": tuple(_safe_text(item) for item in warnings),
                "blockers": tuple(_safe_text(item) for item in blockers),
                "assumptions": tuple(_safe_text(item) for item in assumptions),
                "audit_refs": tuple(_safe_text(item) for item in audit_refs),
                "stale": tuple(_safe_text(item) for item in stale),
                "conflicts": tuple(_safe_text(item) for item in conflicts),
            }
        )
        return PresentationV65(markdown, plain_text, digest, plain_text)


@dataclass(frozen=True, slots=True)
class ScenarioV65:
    scenario_id: str
    assumptions: Mapping[str, str]
    outcomes: Mapping[str, str]
    risks: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    reversibility: str = "unknown"
    confidence: float | None = None
    constraints: Mapping[str, str] = field(default_factory=dict)
    downstream_effects: Mapping[str, str] = field(default_factory=dict)
    failure_modes: tuple[str, ...] = ()
    uncertainty: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise AdvisoryError("scenario_requires_identifier")
        if self.confidence is not None and (
            not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0
        ):
            raise AdvisoryError("scenario_confidence_must_be_between_zero_and_one")
        for field_name in ("assumptions", "outcomes", "constraints", "downstream_effects", "uncertainty"):
            value = getattr(self, field_name)
            object.__setattr__(self, field_name, MappingProxyType(dict(value)))


@dataclass(frozen=True, slots=True)
class ScenarioComparisonV65:
    baseline_id: str
    alternative_id: str
    changed_assumptions: tuple[str, ...]
    changed_outcomes: tuple[str, ...]
    decision_triggers: tuple[str, ...]
    digest: str
    provider_writes: int = 0
    changed_constraints: tuple[str, ...] = ()
    changed_downstream_effects: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
    analysis_label: str = "provider-free counterfactual analysis"


class ScenarioIntelligenceV65:
    """Compare immutable provider-neutral snapshots with deterministic replay."""

    def compare(self, baseline: ScenarioV65, alternative: ScenarioV65) -> ScenarioComparisonV65:
        if baseline.scenario_id == alternative.scenario_id:
            raise AdvisoryError("scenario_ids_must_differ")
        assumption_changes = self._changed_keys(baseline.assumptions, alternative.assumptions)
        outcome_changes = self._changed_keys(baseline.outcomes, alternative.outcomes)
        constraint_changes = self._changed_keys(baseline.constraints, alternative.constraints)
        downstream_changes = self._changed_keys(
            baseline.downstream_effects, alternative.downstream_effects
        )
        uncertainty = tuple(sorted(set(baseline.uncertainty) | set(alternative.uncertainty)))
        triggers = tuple(
            sorted(
                set(alternative.risks)
                | set(alternative.tradeoffs)
                | set(alternative.failure_modes)
                | set(constraint_changes)
            )
        )
        payload = (
            baseline.scenario_id,
            alternative.scenario_id,
            assumption_changes,
            outcome_changes,
            constraint_changes,
            downstream_changes,
            uncertainty,
            triggers,
            baseline.reversibility,
            alternative.reversibility,
            baseline.confidence,
            alternative.confidence,
        )
        return ScenarioComparisonV65(
            baseline_id=baseline.scenario_id,
            alternative_id=alternative.scenario_id,
            changed_assumptions=assumption_changes,
            changed_outcomes=outcome_changes,
            decision_triggers=triggers,
            digest=_digest(payload),
            changed_constraints=constraint_changes,
            changed_downstream_effects=downstream_changes,
            uncertainty=uncertainty,
        )

    @staticmethod
    def _changed_keys(left: Mapping[str, str], right: Mapping[str, str]) -> tuple[str, ...]:
        return tuple(
            sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
        )
