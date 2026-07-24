from __future__ import annotations

from atlas_ros.contracts import KnowledgePackage, ManagementPackage, ReasoningPackage
from atlas_ros.models import PlanningModelRegistry


class ManagementStructureEngine:
    """Builds a provider-independent management package from governed inputs."""

    def __init__(self, registry: PlanningModelRegistry) -> None:
        self._registry = registry

    def structure(
        self,
        reasoning: ReasoningPackage,
        knowledge: KnowledgePackage,
        model_id: str,
        *,
        owner: str | None = None,
        workstream: str | None = None,
    ) -> ManagementPackage:
        if reasoning.correlation_id != knowledge.correlation_id:
            raise ValueError("reasoning and knowledge correlation ids must match")
        model = self._registry.get(model_id)
        values = {"classification": reasoning.classification, **knowledge.facts}
        try:
            responsibility = model.responsibility_template.format_map(values)
            outcome = model.outcome_template.format_map(values)
        except KeyError as exc:
            raise ValueError(f"missing planning-model value: {exc.args[0]}") from exc
        return ManagementPackage(
            correlation_id=reasoning.correlation_id,
            source_component="engines.management_structure",
            responsibility=responsibility,
            desired_outcome=outcome,
            owner=model.default_owner if owner is None else owner,
            workstream=model.default_workstream if workstream is None else workstream,
            decision_points=list(knowledge.unresolved_questions),
        )
