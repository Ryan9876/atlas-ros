from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts import ExecutionPlan, ExecutionStep, ManagementPackage


@dataclass(frozen=True)
class ExecutionPlanningPolicy:
    max_steps: int = 3
    review_threshold: int = 5
    execution_owner: str = "Ryan"

    def __post_init__(self) -> None:
        if self.max_steps < 0:
            raise ValueError("max_steps must be non-negative")
        if self.review_threshold < self.max_steps:
            raise ValueError("review_threshold cannot be below max_steps")
        if not self.execution_owner.strip():
            raise ValueError("execution_owner is required")


class ExecutionPlanner:
    """Projects management outcomes into provider-independent execution objects."""

    def __init__(self, policy: ExecutionPlanningPolicy | None = None) -> None:
        self._policy = policy or ExecutionPlanningPolicy()

    @staticmethod
    def _normalized(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    def plan(
        self,
        management: ManagementPackage,
        *,
        action_id: str,
        destination: str,
        candidate_steps: tuple[str, ...] = (),
        existing_representations: tuple[str, ...] = (),
    ) -> ExecutionPlan:
        reasons: list[str] = []
        existing = {self._normalized(value) for value in existing_representations}
        objective_key = self._normalized(management.desired_outcome)

        if management.owner.strip().casefold() != self._policy.execution_owner.casefold():
            reasons.append("Outcome is not owned by the governed execution owner.")
        if management.decision_points:
            reasons.append("Unresolved management decisions prevent execution projection.")
        if objective_key in existing:
            reasons.append("An equivalent execution representation already exists.")

        unique_candidates: list[str] = []
        seen: set[str] = set()
        for candidate in candidate_steps:
            key = self._normalized(candidate)
            if not key or key in seen or key in existing:
                continue
            seen.add(key)
            unique_candidates.append(candidate.strip())

        review_required = len(unique_candidates) > self._policy.review_threshold
        if review_required:
            reasons.append(
                "Candidate execution scope exceeds the governed review threshold."
            )

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
