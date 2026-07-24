from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from atlas_ros.contracts import (
    CandidateType,
    CompletionState,
    DuplicateFinding,
    ExecutionCandidate,
    ExecutionPlan,
    ExecutionPlanV2,
    ExecutionStep,
    ExecutionStepV2,
    ExistingRepresentation,
    ExistingRepresentationIndex,
    HorizonState,
    ManagementPackage,
    ManagementPackageV2,
    ProjectedObjectType,
    ProjectionDecision,
    ProjectionDecisionStatus,
    ProjectionTestResult,
    RepresentationMatch,
    RepresentationMatchKind,
    TaskBudgetResult,
    deterministic_digest,
)

EventSink = Callable[[str, dict[str, str]], None]
POLICY_VERSION = "execution-planning-v2.0.0"


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _stable_id(prefix: str, payload: object) -> str:
    return f"{prefix}:{deterministic_digest(payload)[:24]}"


def _candidate_signature(candidate: ExecutionCandidate) -> str:
    return deterministic_digest(
        {
            "owner": _normalized(candidate.owner),
            "objective": _normalized(candidate.proposed_objective),
            "done_when": _normalized(candidate.done_when),
            "responsibility_domain": _normalized(candidate.responsibility_domain),
            "workstream": _normalized(candidate.workstream),
            "source_outcome": candidate.source_management_reference,
            "dependencies": sorted(candidate.dependency_references),
        }
    )


def _representation_signature(representation: ExistingRepresentation) -> str:
    if representation.canonical_signature:
        return representation.canonical_signature
    return deterministic_digest(
        {
            "owner": _normalized(representation.owner),
            "objective": _normalized(representation.objective),
            "done_when": _normalized(representation.done_when),
            "responsibility_domain": "",
            "workstream": _normalized(representation.workstream),
            "source_outcome": representation.source_action_id,
            "dependencies": [],
        }
    )


@dataclass(frozen=True)
class ExecutionPlanningPolicy:
    max_steps: int = 3
    review_threshold: int = 5
    execution_owner: str = "Ryan"
    allow_expanded_budget: bool = True
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.max_steps < 0:
            raise ValueError("max_steps must be non-negative")
        if self.review_threshold < self.max_steps:
            raise ValueError("review_threshold cannot be below max_steps")
        if not self.execution_owner.strip():
            raise ValueError("execution_owner is required")
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")


@dataclass(frozen=True)
class CandidateExtractionResult:
    candidates: tuple[ExecutionCandidate, ...]
    candidate_set_digest: str


class ExecutionCandidateExtractor:
    """Extracts explicit execution metadata without model-specific branching."""

    ACTION_KEY = "execution_candidates"

    def __init__(self, event_sink: EventSink | None = None) -> None:
        self._event_sink = event_sink

    @staticmethod
    def _build_candidate(**values: Any) -> ExecutionCandidate:
        unsigned = ExecutionCandidate(candidate_digest="0" * 64, **values)
        return ExecutionCandidate(
            **values,
            candidate_digest=deterministic_digest(unsigned.digest_payload()),
        )

    def extract(self, management: ManagementPackageV2) -> CandidateExtractionResult:
        if not management.verify_digest():
            raise ValueError("Management Package V2 digest verification failed")
        management_reference = (
            f"management-package/v2/{management.artifact_id}/{management.package_digest}"
        )
        parent_done_when = (
            management.completion_evidence_requirements[0]
            if management.completion_evidence_requirements
            else ""
        )
        parent_values: dict[str, Any] = {
            "candidate_id": _stable_id(
                "candidate", {"artifact": management.artifact_id, "kind": "parent"}
            ),
            "correlation_id": management.correlation_id,
            "source_management_reference": management_reference,
            "candidate_type": CandidateType.PARENT_OUTCOME,
            "title": management.desired_outcome,
            "proposed_objective": management.desired_outcome,
            "done_when": parent_done_when,
            "owner": management.owner,
            "responsibility_domain": management.responsibility,
            "workstream": management.workstream,
            "source_section": "management_outcome",
            "source_item_id": management.artifact_id,
            "source_provenance": (management.source_knowledge_reference,),
            "dependency_references": (),
            "execution_ready": management.lifecycle_status == "structurally_complete",
            "earliest_executable_horizon": (
                HorizonState.CURRENT
                if management.lifecycle_status == "structurally_complete"
                else HorizonState.BLOCKED
            ),
            "ambiguities": management.unresolved_items,
            "evidence": management.completion_evidence_requirements,
            "independently_executable": True,
        }
        candidates: list[ExecutionCandidate] = [self._build_candidate(**parent_values)]
        for section in management.sections:
            raw_items = section.content.get(self.ACTION_KEY, ())
            if not isinstance(raw_items, Sequence) or isinstance(raw_items, str | bytes):
                continue
            for index, raw in enumerate(raw_items, 1):
                if not isinstance(raw, Mapping):
                    continue
                candidate_type = CandidateType(
                    str(raw.get("candidate_type", CandidateType.EXECUTABLE_ACTION))
                )
                title = str(raw.get("title", "")).strip()
                objective = str(raw.get("objective", title)).strip()
                if not title or not objective:
                    continue
                horizon = HorizonState(str(raw.get("horizon", HorizonState.CURRENT)))
                completion = CompletionState(
                    str(raw.get("completion_state", CompletionState.OUTSTANDING))
                )
                source_item_id = str(raw.get("source_item_id", f"{section.section_id}:{index}"))
                dependencies = tuple(
                    str(value) for value in raw.get("dependencies", ()) if str(value)
                )
                values = {
                    "candidate_id": str(
                        raw.get(
                            "candidate_id",
                            _stable_id(
                                "candidate",
                                {
                                    "artifact": management.artifact_id,
                                    "section": section.section_id,
                                    "item": source_item_id,
                                    "title": _normalized(title),
                                },
                            ),
                        )
                    ),
                    "correlation_id": management.correlation_id,
                    "source_management_reference": management_reference,
                    "candidate_type": candidate_type,
                    "title": title,
                    "proposed_objective": objective,
                    "done_when": str(raw.get("done_when", "")).strip(),
                    "owner": str(raw.get("owner", management.owner)).strip(),
                    "responsibility_domain": str(
                        raw.get("responsibility_domain", management.responsibility)
                    ).strip(),
                    "workstream": str(raw.get("workstream", management.workstream)).strip(),
                    "source_section": section.section_id,
                    "source_item_id": source_item_id,
                    "source_provenance": tuple(
                        dict.fromkeys(
                            (
                                *section.provenance,
                                *(str(value) for value in raw.get("provenance", ())),
                            )
                        )
                    ),
                    "dependency_references": dependencies,
                    "trigger": str(raw.get("trigger", "")).strip(),
                    "trigger_satisfied": bool(raw.get("trigger_satisfied", False)),
                    "completion_state": completion,
                    "execution_ready": bool(raw.get("execution_ready", False)),
                    "earliest_executable_horizon": horizon,
                    "existing_representation_hints": tuple(
                        str(value)
                        for value in raw.get("existing_representation_hints", ())
                    ),
                    "confidence": float(raw.get("confidence", 1.0)),
                    "assumptions": tuple(str(value) for value in raw.get("assumptions", ())),
                    "ambiguities": tuple(str(value) for value in raw.get("ambiguities", ())),
                    "evidence": tuple(str(value) for value in raw.get("evidence", ())),
                    "can_remain_embedded": bool(raw.get("can_remain_embedded", False)),
                    "improves_execution_clarity": bool(
                        raw.get("improves_execution_clarity", True)
                    ),
                    "independently_executable": bool(
                        raw.get("independently_executable", True)
                    ),
                    "recurrence_required": bool(raw.get("recurrence_required", False)),
                }
                candidates.append(self._build_candidate(**values))

        candidates.extend(self._management_only_candidates(management, management_reference))
        ordered = tuple(
            sorted(
                candidates,
                key=lambda candidate: (
                    candidate.earliest_executable_horizon.value,
                    candidate.source_section,
                    candidate.source_item_id,
                    candidate.candidate_id,
                ),
            )
        )
        digest = deterministic_digest(
            [candidate.candidate_digest for candidate in ordered]
        )
        for candidate in ordered:
            self._emit(
                "candidate_extracted",
                candidate,
                {"candidate_set_digest": digest},
            )
        return CandidateExtractionResult(ordered, digest)

    def _management_only_candidates(
        self,
        management: ManagementPackageV2,
        management_reference: str,
    ) -> list[ExecutionCandidate]:
        groups: tuple[tuple[CandidateType, str, tuple[str, ...]], ...] = (
            (CandidateType.DECISION, "decision", management.decision_points),
            (CandidateType.GOVERNANCE, "governance", management.governance_requirements),
            (CandidateType.APPROVAL, "approval", management.required_approvals),
            (
                CandidateType.EVIDENCE,
                "completion_evidence",
                management.completion_evidence_requirements,
            ),
        )
        results: list[ExecutionCandidate] = []
        for candidate_type, section, values in groups:
            for index, value in enumerate(values, 1):
                fields: dict[str, Any] = {
                    "candidate_id": _stable_id(
                        "candidate",
                        {
                            "artifact": management.artifact_id,
                            "section": section,
                            "value": value,
                        },
                    ),
                    "correlation_id": management.correlation_id,
                    "source_management_reference": management_reference,
                    "candidate_type": candidate_type,
                    "title": value,
                    "proposed_objective": value,
                    "done_when": "",
                    "owner": management.owner,
                    "responsibility_domain": management.responsibility,
                    "workstream": management.workstream,
                    "source_section": section,
                    "source_item_id": f"{section}:{index}",
                    "source_provenance": (management.source_knowledge_reference,),
                    "execution_ready": False,
                    "earliest_executable_horizon": HorizonState.NOT_APPLICABLE,
                    "can_remain_embedded": True,
                    "improves_execution_clarity": False,
                    "independently_executable": False,
                }
                results.append(self._build_candidate(**fields))
        return results

    def _emit(
        self,
        event: str,
        candidate: ExecutionCandidate,
        extra: dict[str, str] | None = None,
    ) -> None:
        if self._event_sink is None:
            return
        fields = {
            "correlation_id": str(candidate.correlation_id),
            "candidate_id": candidate.candidate_id,
            "policy_version": POLICY_VERSION,
            "responsibility_domain": candidate.responsibility_domain,
            "workstream": candidate.workstream,
            "candidate_digest": candidate.candidate_digest,
        }
        fields.update(extra or {})
        self._event_sink(event, fields)


class DuplicateAnalyzer:
    """Applies ordered, conservative duplicate layers."""

    def analyze(
        self,
        candidates: Sequence[ExecutionCandidate],
    ) -> dict[str, DuplicateFinding]:
        ordered = sorted(candidates, key=lambda candidate: candidate.candidate_id)
        seen: list[ExecutionCandidate] = []
        findings: dict[str, DuplicateFinding] = {}
        for candidate in ordered:
            finding = DuplicateFinding(candidate_id=candidate.candidate_id)
            for prior in seen:
                layer = self._match_layer(candidate, prior)
                if layer:
                    finding = DuplicateFinding(
                        candidate_id=candidate.candidate_id,
                        matched_candidate_id=prior.candidate_id,
                        layer=layer,
                        duplicate=True,
                        rationale=f"Matched {prior.candidate_id} by {layer}.",
                    )
                    break
                if self._ambiguous_match(candidate, prior):
                    finding = DuplicateFinding(
                        candidate_id=candidate.candidate_id,
                        matched_candidate_id=prior.candidate_id,
                        layer="conservative_similarity",
                        ambiguous=True,
                        rationale=(
                            f"Candidate resembles {prior.candidate_id}, but the "
                            "evidence is insufficient for automatic suppression."
                        ),
                    )
                    break
            findings[candidate.candidate_id] = finding
            if not finding.duplicate and not finding.ambiguous:
                seen.append(candidate)
        return findings

    @staticmethod
    def _match_layer(left: ExecutionCandidate, right: ExecutionCandidate) -> str:
        if left.candidate_id == right.candidate_id:
            return "candidate_id"
        if _normalized(left.title) == _normalized(right.title):
            return "normalized_title"
        left_objective = (
            _normalized(left.proposed_objective),
            _normalized(left.done_when),
        )
        right_objective = (
            _normalized(right.proposed_objective),
            _normalized(right.done_when),
        )
        if left_objective == right_objective:
            return "objective_done_when"
        if _candidate_signature(left) == _candidate_signature(right):
            return "canonical_signature"
        if (
            left.source_section == right.source_section
            and left.source_item_id
            and left.source_item_id == right.source_item_id
        ):
            return "source_reference"
        if (
            left.candidate_type is CandidateType.PARENT_OUTCOME
            and _normalized(left.proposed_objective) == _normalized(right.title)
        ) or (
            right.candidate_type is CandidateType.PARENT_OUTCOME
            and _normalized(right.proposed_objective) == _normalized(left.title)
        ):
            return "parent_child_equivalence"
        if (
            left.dependency_references
            and left.dependency_references == right.dependency_references
            and _normalized(left.proposed_objective)
            == _normalized(right.proposed_objective)
        ):
            return "dependency_equivalence"
        return ""

    @staticmethod
    def _ambiguous_match(
        left: ExecutionCandidate,
        right: ExecutionCandidate,
    ) -> bool:
        if left.candidate_type is not right.candidate_type:
            return False
        left_title = _normalized(left.title)
        right_title = _normalized(right.title)
        left_tokens = set(left_title.split())
        right_tokens = set(right_title.split())
        differing_tokens = left_tokens ^ right_tokens
        return (
            min(len(left_title), len(right_title)) >= 12
            and bool(differing_tokens)
            and all(token.isalpha() and len(token) >= 4 for token in differing_tokens)
            and SequenceMatcher(None, left_title, right_title).ratio() >= 0.90
        )


class ExistingRepresentationMatcher:
    def match(
        self,
        candidate: ExecutionCandidate,
        index: ExistingRepresentationIndex,
    ) -> RepresentationMatch:
        matches: list[tuple[RepresentationMatchKind, ExistingRepresentation]] = []
        signature = _candidate_signature(candidate)
        for representation in sorted(
            index.representations, key=lambda item: item.representation_id
        ):
            if candidate.candidate_id == representation.source_action_id:
                kind = (
                    RepresentationMatchKind.EXACT_PARENT
                    if representation.representation_type == "parent"
                    else RepresentationMatchKind.EXACT_SUBTASK
                )
                matches.append((kind, representation))
                continue
            exact = (
                signature == _representation_signature(representation)
                or (
                    _normalized(candidate.proposed_objective)
                    == _normalized(representation.objective)
                    and _normalized(candidate.done_when)
                    == _normalized(representation.done_when)
                )
            )
            if exact:
                kind = (
                    RepresentationMatchKind.EQUIVALENT_COMPLETED
                    if representation.state == "completed"
                    else RepresentationMatchKind.EQUIVALENT_OPEN
                )
                matches.append((kind, representation))
                continue
            if _normalized(candidate.title) == _normalized(representation.title):
                matches.append((RepresentationMatchKind.RELATED, representation))

        if not matches:
            return RepresentationMatch(
                candidate_id=candidate.candidate_id,
                outcome=RepresentationMatchKind.NONE,
                rationale="No equivalent provider-neutral representation was found.",
            )
        exact_matches = [
            match for match in matches if match[0] is not RepresentationMatchKind.RELATED
        ]
        if len(exact_matches) > 1:
            return RepresentationMatch(
                candidate_id=candidate.candidate_id,
                outcome=RepresentationMatchKind.AMBIGUOUS,
                representation_ids=tuple(match[1].representation_id for match in exact_matches),
                rationale="Multiple equivalent representations require human review.",
            )
        kind, representation = exact_matches[0] if exact_matches else matches[0]
        return RepresentationMatch(
            candidate_id=candidate.candidate_id,
            outcome=kind,
            representation_ids=(representation.representation_id,),
            rationale=(
                "Matched provider-neutral representation "
                f"{representation.representation_id}."
            ),
        )


class ProgressiveHorizonPolicy:
    @staticmethod
    def effective(candidate: ExecutionCandidate) -> HorizonState:
        if candidate.completion_state is CompletionState.COMPLETE:
            return HorizonState.COMPLETED
        if candidate.ambiguities or (
            candidate.dependency_references and not candidate.execution_ready
        ):
            return HorizonState.BLOCKED
        if (
            candidate.earliest_executable_horizon is HorizonState.CONDITIONAL
            and candidate.trigger_satisfied
        ):
            return HorizonState.CURRENT
        return candidate.earliest_executable_horizon

    @staticmethod
    def transition(
        candidate: ExecutionCandidate,
        *,
        trigger_satisfied: bool = False,
        dependencies_resolved: bool = False,
    ) -> HorizonState:
        if candidate.completion_state is CompletionState.COMPLETE:
            return HorizonState.COMPLETED
        if candidate.earliest_executable_horizon is HorizonState.CONDITIONAL:
            return HorizonState.CURRENT if trigger_satisfied else HorizonState.CONDITIONAL
        if candidate.earliest_executable_horizon is HorizonState.BLOCKED:
            return HorizonState.CURRENT if dependencies_resolved else HorizonState.BLOCKED
        if candidate.earliest_executable_horizon is HorizonState.NEXT:
            return HorizonState.CURRENT if dependencies_resolved else HorizonState.NEXT
        return candidate.earliest_executable_horizon


class ExecutionPlanner:
    """Exclusive provider-independent boundary for execution-object proposals."""

    def __init__(
        self,
        policy: ExecutionPlanningPolicy | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self._policy = policy or ExecutionPlanningPolicy()
        self._event_sink = event_sink

    @staticmethod
    def _normalized(value: str) -> str:
        return _normalized(value)

    def plan(
        self,
        management: ManagementPackage,
        *,
        action_id: str,
        destination: str,
        candidate_steps: tuple[str, ...] = (),
        existing_representations: tuple[str, ...] = (),
    ) -> ExecutionPlan:
        """Preserve the v1 and W03A compatibility contract."""
        reasons: list[str] = []
        existing = {_normalized(value) for value in existing_representations}
        objective_key = _normalized(management.desired_outcome)

        if management.owner.strip().casefold() != self._policy.execution_owner.casefold():
            reasons.append("Outcome is not owned by the governed execution owner.")
        if management.decision_points:
            reasons.append("Unresolved management decisions prevent execution projection.")
        if objective_key in existing:
            reasons.append("An equivalent execution representation already exists.")

        unique_candidates: list[str] = []
        seen: set[str] = set()
        for candidate in candidate_steps:
            key = _normalized(candidate)
            if not key or key in seen or key in existing:
                continue
            seen.add(key)
            unique_candidates.append(candidate.strip())

        review_required = len(unique_candidates) > self._policy.review_threshold
        if review_required:
            reasons.append("Candidate execution scope exceeds the governed review threshold.")

        projected = not reasons
        selected = unique_candidates[: self._policy.max_steps] if projected else []
        steps = [
            ExecutionStep(
                step_id=f"{action_id}:step:{index}",
                title=title,
                done_when=f"{title} is complete and verified.",
                sequence=index,
            )
            for index, title in enumerate(selected, start=1)
        ]
        explanation = (
            "Projected one parent execution outcome with the next meaningful steps."
            if projected
            else "Execution projection was withheld by governed task-economy controls."
        )
        return ExecutionPlan(
            correlation_id=management.correlation_id,
            source_component="planning.execution",
            action_id=action_id,
            objective=management.desired_outcome,
            destination=destination,
            steps=steps,
            authorized=False,
            projection_explanation=explanation,
            non_projection_reasons=reasons,
            review_required=review_required,
        )

    def plan_v2(
        self,
        management: ManagementPackageV2,
        *,
        action_id: str,
        destination_intent: str,
        candidates: Sequence[ExecutionCandidate] | None = None,
        existing_index: ExistingRepresentationIndex | None = None,
        _multiple_parent_outcomes: bool = False,
    ) -> ExecutionPlanV2:
        extraction = ExecutionCandidateExtractor(self._event_sink).extract(management)
        considered = tuple(candidates) if candidates is not None else extraction.candidates
        if not all(candidate.verify_digest() for candidate in considered):
            raise ValueError("Execution Candidate digest verification failed")
        candidate_set_digest = deterministic_digest(
            sorted(candidate.candidate_digest for candidate in considered)
        )
        duplicates = DuplicateAnalyzer().analyze(considered)
        representation_index = existing_index or ExistingRepresentationIndex()
        matcher = ExistingRepresentationMatcher()
        representation_matches = {
            candidate.candidate_id: matcher.match(candidate, representation_index)
            for candidate in considered
        }
        parents = [
            candidate
            for candidate in considered
            if candidate.candidate_type is CandidateType.PARENT_OUTCOME
        ]
        if not parents:
            raise ValueError("Execution Plan V2 requires a parent outcome candidate")
        parent = sorted(parents, key=lambda candidate: candidate.candidate_id)[0]
        parent_results = self._projection_test(
            parent,
            duplicates[parent.candidate_id],
            representation_matches[parent.candidate_id],
        )
        parent_status = self._status_for(
            parent,
            parent_results,
            duplicates[parent.candidate_id],
            representation_matches[parent.candidate_id],
        )
        parent_projected = parent_status is ProjectionDecisionStatus.PROJECT_PARENT

        child_candidates = [
            candidate
            for candidate in considered
            if candidate.candidate_id != parent.candidate_id
            and candidate.candidate_type is not CandidateType.PARENT_OUTCOME
        ]
        evaluated: list[
            tuple[
                ExecutionCandidate,
                tuple[ProjectionTestResult, ...],
                ProjectionDecisionStatus,
            ]
        ] = []
        for candidate in sorted(child_candidates, key=self._candidate_order):
            results = self._projection_test(
                candidate,
                duplicates[candidate.candidate_id],
                representation_matches[candidate.candidate_id],
            )
            status = self._status_for(
                candidate,
                results,
                duplicates[candidate.candidate_id],
                representation_matches[candidate.candidate_id],
            )
            evaluated.append((candidate, results, status))

        eligible = [
            item
            for item in evaluated
            if item[2] is ProjectionDecisionStatus.PROJECT_SUBTASK
        ]
        review_required = len(eligible) > self._policy.review_threshold
        expanded_budget = (
            self._policy.max_steps < len(eligible) <= self._policy.review_threshold
            and self._policy.allow_expanded_budget
            and all(self._expanded_budget_eligible(item[0]) for item in eligible)
        )
        allowed_count = (
            0
            if review_required
            else (
                len(eligible)
                if expanded_budget
                else min(len(eligible), self._policy.max_steps)
            )
        )
        selected_ids = {item[0].candidate_id for item in eligible[:allowed_count]}

        decisions: list[ProjectionDecision] = []
        parent_decision = self._decision(
            parent,
            parent_status,
            parent_results,
            duplicates[parent.candidate_id],
            representation_matches[parent.candidate_id],
            sequence=None,
            parent_relationship="",
        )
        decisions.append(parent_decision)
        sequence = 0
        for candidate, results, status in evaluated:
            final_status = status
            review = False
            if status is ProjectionDecisionStatus.PROJECT_SUBTASK:
                if review_required:
                    final_status = ProjectionDecisionStatus.REVIEW_REQUIRED
                    review = True
                elif candidate.candidate_id not in selected_ids:
                    final_status = ProjectionDecisionStatus.RETAIN_IN_MANAGEMENT
                else:
                    sequence += 1
            decisions.append(
                self._decision(
                    candidate,
                    final_status,
                    results,
                    duplicates[candidate.candidate_id],
                    representation_matches[candidate.candidate_id],
                    sequence=sequence
                    if final_status is ProjectionDecisionStatus.PROJECT_SUBTASK
                    else None,
                    parent_relationship=parent.candidate_id,
                    review_required=review,
                )
            )

        selected_by_id = {candidate.candidate_id: candidate for candidate, _, _ in eligible}
        projected_steps = tuple(
            ExecutionStepV2(
                step_id=f"{action_id}:step:{decision.sequence}",
                title=selected_by_id[decision.candidate_id].title,
                objective=selected_by_id[decision.candidate_id].proposed_objective,
                done_when=selected_by_id[decision.candidate_id].done_when,
                sequence=decision.sequence or 1,
                dependencies=selected_by_id[decision.candidate_id].dependency_references,
                source_candidate_id=decision.candidate_id,
                source_provenance=selected_by_id[decision.candidate_id].source_provenance,
                horizon=decision.horizon,
                projection_rationale=decision.projection_rationale,
            )
            for decision in decisions
            if decision.status is ProjectionDecisionStatus.PROJECT_SUBTASK
        )
        parent_step = (
            ExecutionStepV2(
                step_id=f"{action_id}:parent",
                title=parent.title,
                objective=parent.proposed_objective,
                done_when=parent.done_when,
                sequence=1,
                dependencies=parent.dependency_references,
                source_candidate_id=parent.candidate_id,
                source_provenance=parent.source_provenance,
                horizon=ProgressiveHorizonPolicy.effective(parent),
                projection_rationale="Primary Ryan-owned current-horizon outcome passed all tests.",
            )
            if parent_projected
            else None
        )
        horizon_summary: dict[str, int] = {}
        for candidate in considered:
            horizon = ProgressiveHorizonPolicy.effective(candidate).value
            horizon_summary[horizon] = horizon_summary.get(horizon, 0) + 1

        task_budget = TaskBudgetResult(
            candidate_count=len(eligible),
            projected_subtask_count=len(projected_steps),
            default_limit=self._policy.max_steps,
            review_threshold=self._policy.review_threshold,
            expanded_budget_used=expanded_budget,
            rationale=self._budget_rationale(len(eligible), expanded_budget, review_required),
            compression_alternatives=(
                (
                    "Retain checklist-level detail in the management artifact.",
                    "Split independent outcomes into separately reviewed parent plans.",
                    "Defer next-horizon actions until their prerequisites are true.",
                )
                if review_required
                else ()
            ),
            multiple_parent_outcomes=(
                _multiple_parent_outcomes or len(parents) > 1
            ),
        )
        deferred = tuple(
            decision.candidate_id
            for decision in decisions
            if decision.status is ProjectionDecisionStatus.DEFER_FUTURE_HORIZON
        )
        retained = tuple(
            decision.candidate_id
            for decision in decisions
            if decision.status
            in {
                ProjectionDecisionStatus.RETAIN_IN_MANAGEMENT,
                ProjectionDecisionStatus.WITHHOLD_NOT_EXECUTION_OBJECT,
            }
        )
        human_decisions = tuple(
            dict.fromkeys(
                reason
                for decision in decisions
                if decision.human_decision_required or decision.review_required
                for reason in (
                    decision.non_projection_reasons
                    or ("Governed decomposition review is required.",)
                )
            )
        )
        plan_arguments: dict[str, Any] = {
            "plan_id": _stable_id(
                "execution-plan",
                {
                    "action_id": action_id,
                    "management_digest": management.package_digest,
                    "candidate_set_digest": candidate_set_digest,
                    "policy": self._policy.policy_version,
                },
            ),
            "action_id": action_id,
            "correlation_id": management.correlation_id,
            "source_management_reference": (
                f"management-package/v2/{management.artifact_id}"
            ),
            "source_management_digest": management.package_digest,
            "planner_policy_version": self._policy.policy_version,
            "parent_outcome": parent_step,
            "destination_intent": destination_intent,
            "projected_steps": projected_steps,
            "projection_decisions": tuple(decisions),
            "deferred_candidates": deferred,
            "retained_management_items": retained,
            "duplicate_findings": tuple(
                duplicates[candidate.candidate_id] for candidate in considered
            ),
            "existing_representation_findings": tuple(
                representation_matches[candidate.candidate_id] for candidate in considered
            ),
            "horizon_summary": horizon_summary,
            "task_budget": task_budget,
            "decomposition_review_status": (
                "required" if review_required else "not_required"
            ),
            "human_decision_requirements": human_decisions,
            "projection_explanation": (
                "Split the work into independently valid parent outcomes and projected "
                "this minimal current-horizon Ryan-owned execution path."
                if parent_projected
                and not review_required
                and _multiple_parent_outcomes
                else (
                    "Projected the minimal current-horizon Ryan-owned execution path."
                    if parent_projected and not review_required
                    else "Withheld automatic projection pending governed review or prerequisites."
                )
            ),
            "non_projection_explanations": tuple(
                reason
                for decision in decisions
                for reason in decision.non_projection_reasons
            ),
            "candidate_set_digest": candidate_set_digest,
            "authorized": False,
        }
        unsigned = ExecutionPlanV2(plan_digest="0" * 64, **plan_arguments)
        plan = ExecutionPlanV2(
            **plan_arguments,
            plan_digest=deterministic_digest(unsigned.digest_payload()),
        )
        self._emit_plan(plan, "plan_withheld" if review_required else "plan_generated")
        return plan

    def plan_many_v2(
        self,
        management: ManagementPackageV2,
        *,
        action_id: str,
        destination_intent: str,
        candidates: Sequence[ExecutionCandidate] | None = None,
        existing_index: ExistingRepresentationIndex | None = None,
    ) -> tuple[ExecutionPlanV2, ...]:
        """Propose separate plans only for independently valid parent outcomes.

        With multiple parent outcomes, children must name their parent candidate in
        ``dependency_references``. Unassigned children are withheld rather than
        being attached by guesswork. Exact or ambiguous parent duplicates are never
        emitted as separate plans.
        """
        extraction = ExecutionCandidateExtractor(self._event_sink).extract(management)
        considered = tuple(candidates) if candidates is not None else extraction.candidates
        parents = tuple(
            sorted(
                (
                    candidate
                    for candidate in considered
                    if candidate.candidate_type is CandidateType.PARENT_OUTCOME
                ),
                key=lambda candidate: candidate.candidate_id,
            )
        )
        if len(parents) <= 1:
            return (
                self.plan_v2(
                    management,
                    action_id=action_id,
                    destination_intent=destination_intent,
                    candidates=considered,
                    existing_index=existing_index,
                ),
            )

        parent_findings = DuplicateAnalyzer().analyze(parents)
        proposals: list[ExecutionPlanV2] = []
        for index, parent in enumerate(parents, 1):
            finding = parent_findings[parent.candidate_id]
            if finding.duplicate or finding.ambiguous:
                continue
            children = tuple(
                candidate
                for candidate in considered
                if candidate.candidate_type is not CandidateType.PARENT_OUTCOME
                and parent.candidate_id in candidate.dependency_references
            )
            plan = self.plan_v2(
                management,
                action_id=f"{action_id}:outcome:{index}",
                destination_intent=destination_intent,
                candidates=(parent, *children),
                existing_index=existing_index,
                _multiple_parent_outcomes=True,
            )
            if plan.parent_outcome is not None:
                proposals.append(plan)
        return tuple(proposals)

    def _projection_test(
        self,
        candidate: ExecutionCandidate,
        duplicate: DuplicateFinding,
        representation: RepresentationMatch,
    ) -> tuple[ProjectionTestResult, ...]:
        horizon = ProgressiveHorizonPolicy.effective(candidate)
        executable_type = candidate.candidate_type in {
            CandidateType.PARENT_OUTCOME,
            CandidateType.EXECUTABLE_ACTION,
            CandidateType.RISK_RESPONSE,
        }
        done_when_valid = self._valid_done_when(candidate.done_when)
        unresolved = bool(candidate.ambiguities) or (
            bool(candidate.dependency_references) and not candidate.execution_ready
        )
        existing_suppresses = representation.outcome in {
            RepresentationMatchKind.EXACT_PARENT,
            RepresentationMatchKind.EXACT_SUBTASK,
            RepresentationMatchKind.EQUIVALENT_OPEN,
        } or (
            representation.outcome is RepresentationMatchKind.EQUIVALENT_COMPLETED
            and not candidate.recurrence_required
        )
        conditions = (
            (
                "ryan_ownership",
                candidate.owner.strip().casefold()
                == self._policy.execution_owner.casefold(),
                "owner",
                "Candidate must be owned by Ryan.",
            ),
            (
                "concrete_action",
                executable_type and candidate.independently_executable,
                "concrete_action",
                "Only concrete outcomes or independently executable actions qualify.",
            ),
            (
                "execution_readiness",
                candidate.execution_ready,
                "execution_ready",
                "Scope, result, dependencies, and inputs must be defined.",
            ),
            (
                "binary_completion",
                done_when_valid,
                "done_when",
                "A specific observable Done When condition is required.",
            ),
            (
                "future_attention",
                candidate.completion_state is not CompletionState.COMPLETE,
                "future_attention",
                "Completed work does not require future attention.",
            ),
            (
                "current_horizon",
                horizon is HorizonState.CURRENT,
                "current_horizon",
                f"Effective horizon is {horizon.value}.",
            ),
            (
                "no_unresolved_prerequisite",
                not unresolved,
                "unresolved_prerequisite",
                "Unresolved dependencies or ambiguities block projection.",
            ),
            (
                "not_already_complete",
                candidate.completion_state is not CompletionState.COMPLETE,
                "already_complete",
                "Evidence must not show the action is complete.",
            ),
            (
                "not_duplicate",
                not duplicate.duplicate and not duplicate.ambiguous,
                "duplicate",
                duplicate.rationale or "No duplicate candidate was found.",
            ),
            (
                "not_already_represented",
                not existing_suppresses
                and representation.outcome is not RepresentationMatchKind.AMBIGUOUS,
                "existing_representation",
                representation.rationale,
            ),
            (
                "cannot_remain_embedded",
                not candidate.can_remain_embedded,
                "embedded",
                "Management fields, notes, evidence, and governance remain embedded.",
            ),
            (
                "execution_value",
                candidate.improves_execution_clarity,
                "execution_value",
                "The object must improve execution clarity or verification.",
            ),
            (
                "task_economy_fit",
                executable_type
                and candidate.independently_executable
                and horizon is HorizonState.CURRENT,
                "task_economy",
                "The candidate must be necessary to the minimal executable path.",
            ),
            (
                "provider_independent_validity",
                not any(
                    token in candidate.model_dump_json().casefold()
                    for token in ("todoist_id", "project_id", "section_id", "label_id")
                ),
                "provider_independence",
                "Validity cannot depend on provider object identifiers.",
            ),
        )
        results = tuple(
            ProjectionTestResult(
                condition=name,
                passed=passed,
                reason_code=f"{code}_{'passed' if passed else 'failed'}",
                detail=detail,
            )
            for name, passed, code, detail in conditions
        )
        self._emit_candidate(
            "task_projection_test_passed"
            if all(result.passed for result in results)
            else "task_projection_test_failed",
            candidate,
            {
                "reason_codes": ",".join(
                    result.reason_code for result in results if not result.passed
                )
            },
        )
        return results

    @staticmethod
    def _valid_done_when(value: str) -> bool:
        normalized = _normalized(value)
        generic = {
            "the task is complete",
            "the work is done",
            "this step is complete and verified",
        }
        return len(normalized.split()) >= 4 and normalized not in generic

    def _status_for(
        self,
        candidate: ExecutionCandidate,
        results: tuple[ProjectionTestResult, ...],
        duplicate: DuplicateFinding,
        representation: RepresentationMatch,
    ) -> ProjectionDecisionStatus:
        failed = {result.condition for result in results if not result.passed}
        horizon = ProgressiveHorizonPolicy.effective(candidate)
        if duplicate.duplicate:
            return ProjectionDecisionStatus.SUPPRESS_DUPLICATE
        if duplicate.ambiguous:
            return ProjectionDecisionStatus.REVIEW_REQUIRED
        if (
            representation.outcome
            in {
                RepresentationMatchKind.EXACT_PARENT,
                RepresentationMatchKind.EXACT_SUBTASK,
                RepresentationMatchKind.EQUIVALENT_OPEN,
                RepresentationMatchKind.EQUIVALENT_COMPLETED,
            }
            and not (
                representation.outcome is RepresentationMatchKind.EQUIVALENT_COMPLETED
                and candidate.recurrence_required
            )
        ):
            return ProjectionDecisionStatus.SUPPRESS_EXISTING
        if representation.outcome is RepresentationMatchKind.AMBIGUOUS:
            return ProjectionDecisionStatus.REVIEW_REQUIRED
        if horizon in {HorizonState.NEXT, HorizonState.CONDITIONAL, HorizonState.FUTURE}:
            return ProjectionDecisionStatus.DEFER_FUTURE_HORIZON
        if "ryan_ownership" in failed:
            return ProjectionDecisionStatus.WITHHOLD_NOT_OWNED
        if candidate.completion_state is CompletionState.COMPLETE:
            return ProjectionDecisionStatus.WITHHOLD_ALREADY_COMPLETE
        if "no_unresolved_prerequisite" in failed:
            return ProjectionDecisionStatus.WITHHOLD_UNRESOLVED
        if candidate.candidate_type not in {
            CandidateType.PARENT_OUTCOME,
            CandidateType.EXECUTABLE_ACTION,
            CandidateType.RISK_RESPONSE,
        } or candidate.can_remain_embedded:
            return ProjectionDecisionStatus.WITHHOLD_NOT_EXECUTION_OBJECT
        if failed:
            return ProjectionDecisionStatus.WITHHOLD_NOT_READY
        return (
            ProjectionDecisionStatus.PROJECT_PARENT
            if candidate.candidate_type is CandidateType.PARENT_OUTCOME
            else ProjectionDecisionStatus.PROJECT_SUBTASK
        )

    def _decision(
        self,
        candidate: ExecutionCandidate,
        status: ProjectionDecisionStatus,
        results: tuple[ProjectionTestResult, ...],
        duplicate: DuplicateFinding,
        representation: RepresentationMatch,
        *,
        sequence: int | None,
        parent_relationship: str,
        review_required: bool = False,
    ) -> ProjectionDecision:
        projected = status in {
            ProjectionDecisionStatus.PROJECT_PARENT,
            ProjectionDecisionStatus.PROJECT_SUBTASK,
        }
        reasons = tuple(result.detail for result in results if not result.passed)
        arguments: dict[str, Any] = {
            "candidate_id": candidate.candidate_id,
            "status": status,
            "projected_object_type": (
                ProjectedObjectType.PARENT
                if status is ProjectionDecisionStatus.PROJECT_PARENT
                else (
                    ProjectedObjectType.SUBTASK
                    if status is ProjectionDecisionStatus.PROJECT_SUBTASK
                    else ProjectedObjectType.NONE
                )
            ),
            "parent_relationship": parent_relationship,
            "sequence": sequence,
            "projection_rationale": (
                "Candidate passed every required Task Projection Test condition."
                if projected
                else "Candidate remains outside the automatic execution projection."
            ),
            "non_projection_reasons": () if projected else reasons,
            "task_projection_test": results,
            "horizon": ProgressiveHorizonPolicy.effective(candidate),
            "duplicate_result": duplicate,
            "existing_representation_result": representation,
            "review_required": review_required
            or status is ProjectionDecisionStatus.REVIEW_REQUIRED,
            "human_decision_required": status
            in {
                ProjectionDecisionStatus.REVIEW_REQUIRED,
                ProjectionDecisionStatus.WITHHOLD_UNRESOLVED,
            },
            "evidence": candidate.evidence,
            "policy_version": self._policy.policy_version,
        }
        unsigned = ProjectionDecision(decision_digest="0" * 64, **arguments)
        decision = ProjectionDecision(
            **arguments,
            decision_digest=deterministic_digest(unsigned.digest_payload()),
        )
        self._emit_candidate(
            "candidate_projected" if projected else "candidate_withheld",
            candidate,
            {
                "decision_status": status.value,
                "decision_digest": decision.decision_digest,
                "reason_codes": ",".join(
                    result.reason_code for result in results if not result.passed
                ),
            },
        )
        return decision

    @staticmethod
    def _expanded_budget_eligible(candidate: ExecutionCandidate) -> bool:
        return (
            candidate.independently_executable
            and candidate.execution_ready
            and candidate.improves_execution_clarity
            and not candidate.can_remain_embedded
            and ProgressiveHorizonPolicy.effective(candidate) is HorizonState.CURRENT
            and ExecutionPlanner._valid_done_when(candidate.done_when)
        )

    @staticmethod
    def _candidate_order(candidate: ExecutionCandidate) -> tuple[str, str, str, str]:
        return (
            candidate.workstream,
            candidate.source_section,
            candidate.source_item_id,
            candidate.candidate_id,
        )

    @staticmethod
    def _budget_rationale(count: int, expanded: bool, review: bool) -> str:
        if review:
            return (
                f"{count} independently eligible subtasks exceed the five-step "
                "automatic limit; decomposition review is required."
            )
        if expanded:
            return (
                f"{count} distinct current-horizon subtasks each passed the full "
                "projection test, so the governed four-or-five-step allowance applies."
            )
        return "The plan uses the default zero-to-three minimal executable path."

    def _emit_candidate(
        self,
        event: str,
        candidate: ExecutionCandidate,
        extra: dict[str, str],
    ) -> None:
        if self._event_sink is None:
            return
        fields = {
            "correlation_id": str(candidate.correlation_id),
            "candidate_id": candidate.candidate_id,
            "policy_version": self._policy.policy_version,
            "responsibility_domain": candidate.responsibility_domain,
            "workstream": candidate.workstream,
            "candidate_digest": candidate.candidate_digest,
        }
        fields.update(extra)
        self._event_sink(event, fields)

    def _emit_plan(self, plan: ExecutionPlanV2, event: str) -> None:
        if self._event_sink:
            self._event_sink(
                event,
                {
                    "correlation_id": str(plan.correlation_id),
                    "plan_id": plan.plan_id,
                    "policy_version": plan.planner_policy_version,
                    "decision_status": plan.decomposition_review_status,
                    "plan_digest": plan.plan_digest,
                },
            )
