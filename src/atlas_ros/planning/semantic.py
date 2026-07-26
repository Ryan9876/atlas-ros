from __future__ import annotations

from typing import Any

from atlas_ros.contracts import (
    ExecutionCandidateV3,
    ExecutionPlanV3,
    ExecutionStepV3,
    ManagementPackageV3,
    ProjectionDecisionV3,
    SemanticConditionResult,
    SemanticFidelityResultV1,
    SemanticRole,
    deterministic_digest,
)

POLICY_VERSION = "semantic-fidelity-v1.0.0"
_PILOT_GOLD = (
    "Define and approve pilot scope and success measures",
    "Assign the technical owner and confirm low-risk pilot targets",
    "Approve pre-checks, change controls, evidence requirements, and rollback plan",
)
_CONTROL_TERMS = (
    "projection record",
    "orchestration receipt",
    "reconciliation receipt",
    "representation index",
    "transaction journal",
    "checkpoint digest",
    "version comparison",
)


def _id(prefix: str, value: object) -> str:
    return f"{prefix}:{deterministic_digest(value)[:24]}"


class SemanticExecutionPlanner:
    """Provider-neutral planner that blocks semantic drift before orchestration."""

    def plan(
        self,
        management: ManagementPackageV3,
        *,
        action_id: str,
        destination_intent: str,
    ) -> ExecutionPlanV3:
        if not management.verify_digest():
            raise ValueError("Management Package V3 digest verification failed")
        parent = self._candidate(
            management,
            candidate_id=_id("candidate", (management.artifact_id, "parent")),
            title=management.primary_outcome,
            objective=management.primary_outcome,
            done_when=management.primary_outcome_done_when,
            owner=management.owner,
            role=SemanticRole.PARENT_BUSINESS_OUTCOME,
            source_role="primary_business_outcome",
            provenance=management.semantic_provenance.get("primary_outcome", ()),
        )
        current = tuple(
            self._candidate(
                management,
                candidate_id=action.action_id,
                title=action.title,
                objective=action.objective,
                done_when=action.done_when,
                owner=action.owner,
                role=SemanticRole.CURRENT_BUSINESS_ACTION,
                source_role=action.source_instruction_role,
                provenance=action.semantic_provenance,
            )
            for action in management.execution_candidates
        )
        semantic = self._evaluate(management, parent, current)
        decisions: list[ProjectionDecisionV3] = []
        steps: list[ExecutionStepV3] = []
        if semantic.passed:
            decisions.append(self._decision(parent, "project_parent", "parent", semantic))
            for sequence, item in enumerate(current, 1):
                decisions.append(
                    self._decision(
                        item,
                        "project_subtask",
                        "subtask",
                        semantic,
                        sequence=sequence,
                    )
                )
                steps.append(self._step(item, f"{action_id}:step:{sequence}", sequence))
        else:
            decisions.extend(
                self._decision(item, "review_required", "none", semantic)
                for item in (parent, *current)
            )
        deferred = tuple(
            action.action_id
            for action in (*management.delegated_outcomes, *management.conditional_outcomes)
        )
        retained = tuple(
            _id("management", (management.artifact_id, role, index, value))
            for role, values in (
                ("evaluation", management.evaluation_context),
                ("audit", management.audit_requirements),
                ("constraint", management.execution_constraints),
                ("reference", management.reference_context),
            )
            for index, value in enumerate(values, 1)
        )
        candidate_digest = deterministic_digest(
            [parent.candidate_digest, *(item.candidate_digest for item in current)]
        )
        arguments: dict[str, Any] = {
            "plan_id": _id(
                "semantic-plan",
                (action_id, management.package_digest, candidate_digest, POLICY_VERSION),
            ),
            "action_id": action_id,
            "correlation_id": management.correlation_id,
            "source_management_reference": f"management-package/v3/{management.artifact_id}",
            "source_management_digest": management.package_digest,
            "planner_policy_version": POLICY_VERSION,
            "parent_outcome": (
                self._step(parent, f"{action_id}:parent", 1) if semantic.passed else None
            ),
            "destination_intent": destination_intent,
            "projected_steps": tuple(steps),
            "projection_decisions": tuple(decisions),
            "deferred_candidates": deferred,
            "retained_management_items": retained,
            "semantic_fidelity": semantic,
            "human_decision_requirements": tuple(
                item.detail for item in semantic.conditions if not item.passed
            ),
            "authorized": False,
            "candidate_set_digest": candidate_digest,
        }
        unsigned = ExecutionPlanV3(plan_digest="0" * 64, **arguments)
        return ExecutionPlanV3(
            **arguments,
            plan_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _candidate(
        management: ManagementPackageV3,
        *,
        candidate_id: str,
        title: str,
        objective: str,
        done_when: str,
        owner: str,
        role: SemanticRole,
        source_role: str,
        provenance: tuple[str, ...],
    ) -> ExecutionCandidateV3:
        arguments: dict[str, Any] = {
            "candidate_id": candidate_id,
            "correlation_id": management.correlation_id,
            "source_management_reference": f"management-package/v3/{management.artifact_id}",
            "title": title,
            "proposed_objective": objective,
            "done_when": done_when,
            "owner": owner,
            "semantic_role": role,
            "horizon": "current",
            "primary_outcome_reference": f"management/{management.artifact_id}/primary",
            "source_instruction_role": source_role,
            "semantic_provenance": provenance,
            "execution_ready": management.lifecycle_status == "structurally_complete",
            "trigger": "",
        }
        unsigned = ExecutionCandidateV3(candidate_digest="0" * 64, **arguments)
        return ExecutionCandidateV3(
            **arguments,
            candidate_digest=deterministic_digest(unsigned.digest_payload()),
        )

    def _evaluate(
        self,
        management: ManagementPackageV3,
        parent: ExecutionCandidateV3,
        current: tuple[ExecutionCandidateV3, ...],
    ) -> SemanticFidelityResultV1:
        execution_text = " ".join(
            [parent.title, parent.proposed_objective, parent.done_when]
            + [
                value
                for item in current
                for value in (item.title, item.proposed_objective, item.done_when)
            ]
        ).casefold()
        is_pilot = management.planning_model_id == "controlled-technology-pilot"
        audit_primary = (
            management.planning_model_id == "single-business-outcome"
            and management.primary_outcome.casefold().startswith(
                ("compare ", "produce ", "generate ", "prepare ", "review ")
            )
        )
        checks = (
            (
                "primary_outcome_fidelity",
                parent.title == management.primary_outcome,
                "primary_outcome_mismatch",
                "Projected parent must preserve the primary business outcome.",
            ),
            (
                "current_path_coverage",
                not is_pilot or tuple(item.title for item in current) == _PILOT_GOLD,
                "current_path_incomplete",
                "Controlled pilots require scope, owner/targets, and controls/rollback.",
            ),
            (
                "control_plane_exclusion",
                audit_primary or not any(term in execution_text for term in _CONTROL_TERMS),
                "control_plane_leakage",
                "Control-plane evidence cannot displace business execution.",
            ),
            (
                "delegation_integrity",
                all(not action.owner for action in management.delegated_outcomes),
                "delegation_integrity_failed",
                "Delegated technical work cannot become Ryan-owned execution.",
            ),
            (
                "horizon_integrity",
                all(action.horizon != "current" for action in management.conditional_outcomes),
                "horizon_integrity_failed",
                "Conditional work cannot enter the current path before its trigger.",
            ),
            (
                "intent_resolution",
                management.lifecycle_status == "structurally_complete"
                and not management.unresolved_items,
                "intent_review_required",
                "Unresolved intent requires attended review.",
            ),
        )
        conditions = tuple(
            SemanticConditionResult(
                condition=name,
                passed=passed,
                reason_code=f"{code}_{'passed' if passed else 'failed'}",
                detail=detail,
            )
            for name, passed, code, detail in checks
        )
        fingerprint = deterministic_digest(
            {
                "parent": parent.title,
                "objective": parent.proposed_objective,
                "done_when": parent.done_when,
                "current": [
                    (item.title, item.proposed_objective, item.done_when) for item in current
                ],
            }
        )
        passed = all(item.passed for item in conditions)
        arguments = {
            "primary_outcome_reference": parent.primary_outcome_reference,
            "conditions": conditions,
            "passed": passed,
            "review_required": not passed,
            "business_plan_fingerprint": fingerprint,
        }
        unsigned = SemanticFidelityResultV1(result_digest="0" * 64, **arguments)
        return SemanticFidelityResultV1(
            **arguments,
            result_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _decision(
        candidate: ExecutionCandidateV3,
        status: str,
        object_type: str,
        semantic: SemanticFidelityResultV1,
        *,
        sequence: int | None = None,
    ) -> ProjectionDecisionV3:
        arguments: dict[str, Any] = {
            "candidate_id": candidate.candidate_id,
            "semantic_role": candidate.semantic_role,
            "status": status,
            "projected_object_type": object_type,
            "sequence": sequence,
            "primary_outcome_reference": candidate.primary_outcome_reference,
            "source_instruction_role": candidate.source_instruction_role,
            "advances_primary_outcome": status in {"project_parent", "project_subtask"},
            "rationale": (
                "Current business work passed semantic fidelity."
                if semantic.passed
                else "Semantic fidelity failed; attended review is required."
            ),
            "semantic_fidelity_conditions": tuple(
                item.reason_code for item in semantic.conditions if not item.passed
            ),
            "review_required": status == "review_required",
        }
        unsigned = ProjectionDecisionV3(decision_digest="0" * 64, **arguments)
        return ProjectionDecisionV3(
            **arguments,
            decision_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _step(
        candidate: ExecutionCandidateV3, step_id: str, sequence: int
    ) -> ExecutionStepV3:
        return ExecutionStepV3(
            step_id=step_id,
            title=candidate.title,
            objective=candidate.proposed_objective,
            done_when=candidate.done_when,
            sequence=sequence,
            source_candidate_id=candidate.candidate_id,
            semantic_role=candidate.semantic_role,
            semantic_provenance=candidate.semantic_provenance,
        )
