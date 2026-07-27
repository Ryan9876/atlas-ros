"""Provider-free v6.5 governed execution intelligence.

This module is intentionally advisory.  It has no provider imports, I/O, mutable
global state, or authority to create, update, delete, schedule, send, authorize,
or execute work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from html import escape
from json import dumps
from re import sub
from typing import Iterable, Mapping, Sequence


def _digest(value: object) -> str:
    return sha256(dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class AdvisoryError(ValueError):
    """A fail-closed v6.5 advisory validation error."""


class AuthorityTier(StrEnum):
    ORGANIZATION_POLICY = "organization_policy"
    RELEASE_CONTROL = "release_control"
    APPROVED_STANDARD = "approved_standard"
    PREFERENCE = "preference"


_TIER_ORDER = {
    AuthorityTier.ORGANIZATION_POLICY: 0,
    AuthorityTier.RELEASE_CONTROL: 1,
    AuthorityTier.APPROVED_STANDARD: 2,
    AuthorityTier.PREFERENCE: 3,
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


@dataclass(frozen=True, slots=True)
class FrameworkCompositionV65:
    rules: tuple[FrameworkRuleV65, ...]
    warnings: tuple[str, ...]
    digest: str


class GovernedFrameworkComposerV65:
    """Composes compatible rules with deterministic precedence and fail-closed conflicts."""

    def compose(self, rules: Sequence[FrameworkRuleV65]) -> FrameworkCompositionV65:
        seen: dict[str, FrameworkRuleV65] = {}
        warnings: list[str] = []
        for rule in sorted(rules, key=lambda item: (_TIER_ORDER[item.tier], item.rule_id)):
            if not rule.effective:
                warnings.append(f"stale_or_inactive:{rule.rule_id}")
                continue
            prior = seen.get(rule.rule_id)
            if prior is None:
                seen[rule.rule_id] = rule
                continue
            if prior.requirement != rule.requirement:
                raise AdvisoryError(f"conflicting_rule:{rule.rule_id}")
            if _TIER_ORDER[rule.tier] < _TIER_ORDER[prior.tier]:
                seen[rule.rule_id] = rule
            elif prior.immutable and rule.tier == AuthorityTier.PREFERENCE:
                warnings.append(f"lower_authority_ignored:{rule.rule_id}")
        ordered = tuple(sorted(seen.values(), key=lambda item: (_TIER_ORDER[item.tier], item.rule_id)))
        payload = [(r.rule_id, r.requirement, r.tier, r.source_version, r.source_ref, r.immutable) for r in ordered]
        return FrameworkCompositionV65(ordered, tuple(sorted(warnings)), _digest(payload))


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


@dataclass(frozen=True, slots=True)
class MinimumEffectivePathV65:
    steps: tuple[PathStepV65, ...]
    blockers: tuple[str, ...]
    digest: str


class MinimumEffectivePathPlannerV65:
    """Returns the shortest qualified topological path without dropping mandatory controls."""

    def plan(self, steps: Sequence[PathStepV65], targets: Iterable[str]) -> MinimumEffectivePathV65:
        index = {step.step_id: step for step in steps}
        if len(index) != len(steps):
            raise AdvisoryError("duplicate_path_step")
        required = set(targets) | {step.step_id for step in steps if step.mandatory}
        pending = list(required)
        while pending:
            step_id = pending.pop()
            step = index.get(step_id)
            if step is None:
                raise AdvisoryError(f"missing_prerequisite:{step_id}")
            for prerequisite in step.prerequisites:
                if prerequisite not in required:
                    required.add(prerequisite)
                    pending.append(prerequisite)
        ordered: list[PathStepV65] = []
        remaining = set(required)
        while remaining:
            eligible = sorted(
                step_id for step_id in remaining
                if set(index[step_id].prerequisites).isdisjoint(remaining)
            )
            if not eligible:
                raise AdvisoryError("cyclic_path_prerequisites")
            for step_id in eligible:
                ordered.append(index[step_id])
                remaining.remove(step_id)
        blockers = tuple(
            f"unknown:{step.step_id}:{field_name}"
            for step in ordered
            for field_name, value in (("risk", step.risk), ("reversibility", step.reversibility), ("cost", step.cost))
            if value == "unknown"
        )
        return MinimumEffectivePathV65(tuple(ordered), blockers, _digest([step.step_id for step in ordered]))


class ExecutionStateV65(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PARTIAL_FAILURE = "partial_failure"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


_ALLOWED = {
    ExecutionStateV65.PENDING: {ExecutionStateV65.READY, ExecutionStateV65.BLOCKED},
    ExecutionStateV65.READY: {ExecutionStateV65.IN_PROGRESS, ExecutionStateV65.BLOCKED},
    ExecutionStateV65.IN_PROGRESS: {ExecutionStateV65.SUCCEEDED, ExecutionStateV65.PARTIAL_FAILURE, ExecutionStateV65.FAILED, ExecutionStateV65.BLOCKED},
    ExecutionStateV65.PARTIAL_FAILURE: {ExecutionStateV65.READY, ExecutionStateV65.BLOCKED, ExecutionStateV65.FAILED},
    ExecutionStateV65.BLOCKED: {ExecutionStateV65.READY, ExecutionStateV65.FAILED},
    ExecutionStateV65.SUCCEEDED: set(),
    ExecutionStateV65.FAILED: set(),
}


@dataclass(frozen=True, slots=True)
class ExecutionEventV65:
    event_id: str
    from_state: ExecutionStateV65
    to_state: ExecutionStateV65
    evidence_refs: tuple[str, ...] = ()
    idempotency_key: str = ""
    detail: str = ""


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

    def transition(self, event: ExecutionEventV65) -> "ExecutionRecordV65":
        if self.authority_create or self.authority_update or self.authority_delete or self.authority_schedule or self.authority_send_message or self.authority_authorize or self.authority_execute or self.provider_writes:
            raise AdvisoryError("execution_intelligence_must_remain_provider_free")
        if event.from_state != self.state or event.to_state not in _ALLOWED[self.state]:
            raise AdvisoryError("invalid_execution_transition")
        if event.idempotency_key and any(item.idempotency_key == event.idempotency_key for item in self.events):
            return self
        if event.to_state == ExecutionStateV65.SUCCEEDED and not event.evidence_refs:
            raise AdvisoryError("completion_requires_evidence")
        return ExecutionRecordV65(self.record_id, event.to_state, self.events + (event,), self.receipts + event.evidence_refs)


@dataclass(frozen=True, slots=True)
class PresentationV65:
    executive: str
    technical: str
    audit_digest: str


def _clean(text: str) -> str:
    return sub(r"[\x00-\x1f<>]", "", text).strip()


class ExecutionPresenterV65:
    """Renders evidence-labelled views without claiming unverified completion."""

    def render(self, *, facts: Sequence[str], actions: Sequence[str], warnings: Sequence[str], blockers: Sequence[str], assumptions: Sequence[str], next_steps: Sequence[str], audit_refs: Sequence[str]) -> PresentationV65:
        sections = (
            ("Verified facts", facts), ("Actions", actions), ("Warnings", warnings),
            ("Blockers", blockers), ("Assumptions", assumptions), ("Next steps", next_steps),
            ("Audit references", audit_refs),
        )
        markdown = "\n\n".join(f"## {name}\n" + ("\n".join(f"- {_clean(value)}" for value in values) if values else "- None") for name, values in sections)
        technical = escape(markdown)
        return PresentationV65(markdown, technical, _digest({"markdown": markdown, "audit_refs": tuple(audit_refs)}))


@dataclass(frozen=True, slots=True)
class ScenarioV65:
    scenario_id: str
    assumptions: Mapping[str, str]
    outcomes: Mapping[str, str]
    risks: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    reversibility: str = "unknown"
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ScenarioComparisonV65:
    baseline_id: str
    alternative_id: str
    changed_assumptions: tuple[str, ...]
    changed_outcomes: tuple[str, ...]
    decision_triggers: tuple[str, ...]
    digest: str
    provider_writes: int = 0


class ScenarioIntelligenceV65:
    """Compares immutable snapshots; it does not plan, authorize, or execute."""

    def compare(self, baseline: ScenarioV65, alternative: ScenarioV65) -> ScenarioComparisonV65:
        if baseline.scenario_id == alternative.scenario_id:
            raise AdvisoryError("scenario_ids_must_differ")
        assumption_changes = tuple(sorted(
            key for key in set(baseline.assumptions) | set(alternative.assumptions)
            if baseline.assumptions.get(key) != alternative.assumptions.get(key)
        ))
        outcome_changes = tuple(sorted(
            key for key in set(baseline.outcomes) | set(alternative.outcomes)
            if baseline.outcomes.get(key) != alternative.outcomes.get(key)
        ))
        triggers = tuple(sorted(set(alternative.risks) | set(alternative.tradeoffs)))
        payload = (baseline.scenario_id, alternative.scenario_id, assumption_changes, outcome_changes, triggers)
        return ScenarioComparisonV65(baseline.scenario_id, alternative.scenario_id, assumption_changes, outcome_changes, triggers, _digest(payload))
