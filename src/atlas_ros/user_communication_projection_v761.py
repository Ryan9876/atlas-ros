"""Governed user-model projection for Atlas ROS v7.6.1."""
from __future__ import annotations

from atlas_ros.intent_learning_v750 import ClarificationDecisionV1, ClarificationStatus
from atlas_ros.intent_memory_v760 import GovernedIntentEvidenceV1
from atlas_ros.user_communication_contracts_v761 import (
    CommunicationPreferenceV1,
    CommunicationSourceEvidenceV1,
    ContradictionState,
    IntegratedUserModelProjectionV1,
    PreferenceConfirmationState,
)

def build_user_model_projection(
    *,
    projection_id: str,
    profile_version: str,
    user_id: str,
    workspace_id: str,
    generated_at: str,
    preferences: tuple[CommunicationPreferenceV1, ...],
    source_evidence: tuple[CommunicationSourceEvidenceV1, ...],
    governed_evidence: tuple[GovernedIntentEvidenceV1, ...],
) -> IntegratedUserModelProjectionV1:
    preference_ids = tuple(sorted(item.preference_id for item in preferences))
    if len(set(preference_ids)) != len(preference_ids):
        raise ValueError("preference identifiers must be unique")
    source_by_id = {item.source_id: item for item in source_evidence}
    governed_by_id = {item.evidence_id: item for item in governed_evidence}
    if len(source_by_id) != len(source_evidence):
        raise ValueError("source evidence identifiers must be unique")
    if len(governed_by_id) != len(governed_evidence):
        raise ValueError("governed evidence identifiers must be unique")
    for item in governed_evidence:
        if item.context_key.scope.user_id != user_id:
            raise ValueError("cross-user governed evidence is prohibited")
    referenced_sources = {
        reference for item in preferences for reference in item.evidence_references
    }
    if not referenced_sources.issubset(source_by_id):
        raise ValueError("every preference evidence reference must resolve")
    referenced_governed = {
        evidence_id
        for source in source_evidence
        for evidence_id in source.governed_intent_evidence_ids
    }
    if not referenced_governed.issubset(governed_by_id):
        raise ValueError("source evidence must resolve to governed v7.6 evidence")
    contradictions = tuple(
        sorted(
            item.preference_id
            for item in preferences
            if item.contradiction_state is ContradictionState.OPEN
            or item.confirmation_state is PreferenceConfirmationState.CONTRADICTED
        )
    )
    return IntegratedUserModelProjectionV1(
        projection_id=projection_id,
        profile_version=profile_version,
        user_id=user_id,
        workspace_id=workspace_id,
        generated_at=generated_at,
        preference_ids=preference_ids,
        preference_digests=tuple(
            sorted((item.preference_id, item.deterministic_digest) for item in preferences)
        ),
        governed_evidence_ids=tuple(sorted(referenced_governed)),
        source_evidence_digests=tuple(
            sorted((item.source_id, item.deterministic_digest) for item in source_evidence)
        ),
        contradiction_preference_ids=contradictions,
    )


def preserve_predecessor_clarification(
    decision: ClarificationDecisionV1,
) -> ClarificationDecisionV1:
    """Return the accepted v7.5 clarification result unchanged and provider-write free."""
    if (
        decision.clarification_status is ClarificationStatus.REQUIRED
        and (decision.todoist_write_allowed or decision.provider_writes)
    ):
        raise ValueError("required clarification must remain provider-write free")
    return decision
