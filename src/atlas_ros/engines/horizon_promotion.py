from __future__ import annotations

from atlas_ros.contracts.coherence_v1 import HorizonEvidenceV1, HorizonPromotionProposalV1
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.semantic_v1 import ManagementPackageV3


class AttendedHorizonPromotionEngine:
    """Proposes the next horizon transition without creating provider objects."""

    def evaluate(
        self,
        management: ManagementPackageV3,
        evidence: HorizonEvidenceV1,
    ) -> HorizonPromotionProposalV1:
        if management.planning_model_id != "controlled-technology-pilot":
            raise ValueError("horizon promotion currently supports controlled technology pilots")
        future = tuple(
            dict.fromkeys(
                action.title
                for action in (*management.delegated_outcomes, *management.conditional_outcomes)
            )
        )
        if not evidence.scope_and_success_approved:
            return self._proposal(
                current_checkpoint="Define and approve pilot scope and success measures",
                transition="retain_scope_checkpoint",
                eligible=False,
                rationale="Scope and success measures remain the current checkpoint.",
                retained=future,
            )
        if not (
            evidence.technical_owner_confirmed and evidence.low_risk_targets_confirmed
        ):
            return self._proposal(
                current_checkpoint="Assign the technical owner and confirm low-risk pilot targets",
                transition="retain_owner_and_targets_checkpoint",
                eligible=False,
                rationale="Technical ownership and low-risk targets must be confirmed together.",
                retained=future,
            )
        if not evidence.controls_and_rollback_approved:
            return self._proposal(
                current_checkpoint=(
                    "Approve pre-checks, change controls, evidence requirements, and rollback plan"
                ),
                transition="retain_controls_checkpoint",
                eligible=False,
                rationale="Controls, evidence requirements, and rollback approval remain incomplete.",
                retained=future,
            )
        if not evidence.technical_execution_complete:
            return self._proposal(
                current_checkpoint="Build and execute the technical pilot",
                transition="authorize_delegated_execution",
                eligible=True,
                rationale=(
                    "The delegated technical pilot is eligible for a separate attended authorization."
                ),
                retained=future,
            )
        if not evidence.evidence_complete:
            return self._proposal(
                current_checkpoint="Collect and verify pilot execution evidence",
                transition="collect_execution_evidence",
                eligible=True,
                rationale="Execution is complete, but decision evidence is not yet complete.",
                retained=future,
            )
        if evidence.go_no_go_decision == "pending":
            return self._proposal(
                current_checkpoint="Review pilot evidence and record the go/no-go decision",
                transition="propose_go_no_go_review",
                eligible=True,
                rationale="Complete evidence makes the conditional decision review eligible.",
                retained=future,
            )
        if evidence.go_no_go_decision == "go":
            return self._proposal(
                current_checkpoint="Retain expansion for separate rollout approval",
                transition="retain_expansion_for_separate_approval",
                eligible=False,
                rationale="A go decision does not itself authorize expansion beyond the pilot.",
                retained=future,
            )
        return self._proposal(
            current_checkpoint="Close the pilot without expansion",
            transition="close_without_expansion",
            eligible=True,
            rationale="The no-go decision closes the pilot while preserving the evidence record.",
            retained=future,
        )

    @staticmethod
    def _proposal(
        *,
        current_checkpoint: str,
        transition: str,
        eligible: bool,
        rationale: str,
        retained: tuple[str, ...],
    ) -> HorizonPromotionProposalV1:
        values: dict[str, object] = {
            "current_checkpoint": current_checkpoint,
            "proposed_transition": transition,
            "eligible": eligible,
            "attended_authorization_required": True,
            "provider_writes": 0,
            "rationale": rationale,
            "retained_future_outcomes": retained,
        }
        unsigned = HorizonPromotionProposalV1(proposal_digest="0" * 64, **values)
        return HorizonPromotionProposalV1(
            **values,
            proposal_digest=deterministic_digest(unsigned.digest_payload()),
        )
