from __future__ import annotations

from atlas_ros.contracts.coherence_v1 import HorizonPromotionProposalV1


class HorizonPromotionEngine:
    """Provider-free attended horizon re-evaluation for controlled pilots."""

    def evaluate(
        self,
        *,
        scope_approved: bool,
        owner_targets_confirmed: bool,
        controls_rollback_approved: bool,
        execution_evidence_complete: bool,
        go_decision: bool,
    ) -> HorizonPromotionProposalV1:
        if not scope_approved:
            return self._proposal(
                "scope_definition",
                "scope_definition",
                "Define and approve pilot scope and success measures",
                False,
                "Scope approval remains the first unresolved current checkpoint.",
            )
        if not owner_targets_confirmed:
            return self._proposal(
                "scope_approved",
                "ownership_and_targets",
                "Assign the technical owner and confirm low-risk pilot targets",
                True,
                "Scope is approved; ownership and targets are eligible for attended confirmation.",
            )
        if not controls_rollback_approved:
            return self._proposal(
                "ownership_and_targets_confirmed",
                "controls_and_rollback",
                "Approve pre-checks, change controls, evidence requirements, and rollback plan",
                True,
                "Ownership and targets are confirmed; controls and rollback are next.",
            )
        if not execution_evidence_complete:
            return self._proposal(
                "pilot_authorization_ready",
                "delegated_execution",
                "Authorize the assigned technical owner to build and execute the pilot",
                True,
                (
                    "All current governance checkpoints are complete; delegated execution "
                    "is eligible for separate attended authorization."
                ),
            )
        if not go_decision:
            return self._proposal(
                "execution_evidence_complete",
                "conditional_review",
                "Review pilot evidence and record the go/no-go decision",
                True,
                (
                    "Execution evidence is complete; the conditional review is eligible "
                    "for attended promotion."
                ),
            )
        return self._proposal(
            "go_decision_recorded",
            "future_rollout",
            "Prepare a separately authorized expansion plan",
            True,
            "An affirmative decision permits a separately approved future rollout plan.",
        )

    @staticmethod
    def _proposal(
        current_stage: str,
        proposed_stage: str,
        proposed_action: str,
        eligible: bool,
        rationale: str,
    ) -> HorizonPromotionProposalV1:
        return HorizonPromotionProposalV1(
            current_stage=current_stage,
            proposed_stage=proposed_stage,
            proposed_action=proposed_action,
            eligible=eligible,
            attended_authorization_required=True,
            provider_writes=0,
            rationale=rationale,
        )
