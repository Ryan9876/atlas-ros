from __future__ import annotations

from atlas_ros.contracts import (
    KnowledgePackageV2,
    ManagementPackageV3,
    ReasoningPackageV4,
    deterministic_digest,
)
from atlas_ros.engines.management_structure import (
    ManagementStructureEngine as BaseManagementStructureEngine,
)


class ManagementStructureEngine(BaseManagementStructureEngine):
    """Management structure with explicit reasoning-coherence evidence."""

    def structure_v3(
        self,
        reasoning: ReasoningPackageV4,
        knowledge: KnowledgePackageV2,
        *,
        owner: str | None = None,
        workstream: str | None = None,
    ) -> ManagementPackageV3:
        base = super().structure_v3(
            reasoning,
            knowledge,
            owner=owner,
            workstream=workstream,
        )
        coherence_items = (
            reasoning.coherence_result.material_contradictions
            if reasoning.coherence_result is not None
            and reasoning.coherence_result.review_required
            else ()
        )
        unresolved = tuple(
            dict.fromkeys(
                (
                    *base.unresolved_items,
                    *reasoning.intent_partition_ambiguities,
                    *reasoning.unresolved_planning_questions,
                    *coherence_items,
                )
            )
        )
        lifecycle = (
            "decision_required"
            if reasoning.requires_human_decision or unresolved
            else "structurally_complete"
        )
        data = base.model_dump(mode="python")
        data.update(
            {
                "responsibility": reasoning.responsibility_domain,
                "workstream": reasoning.workstream if workstream is None else workstream,
                "confidence_dimensions": reasoning.confidence_dimensions,
                "reasoning_coherence": reasoning.coherence_result,
                "user_facing_summary": reasoning.user_facing_summary,
                "unresolved_items": unresolved,
                "lifecycle_status": lifecycle,
                "package_digest": "0" * 64,
            }
        )
        unsigned = ManagementPackageV3(**data)
        data["package_digest"] = deterministic_digest(unsigned.digest_payload())
        return ManagementPackageV3(**data)
