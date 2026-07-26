from __future__ import annotations

from typing import Any

from atlas_ros.contracts.models import ContractKind, deterministic_digest
from atlas_ros.contracts.reasoning_v62 import EnhancedReasoningPackageV62
from atlas_ros.contracts.v62 import (
    ClarificationStatus,
    PlanningMemoryEntry,
    PlanningStyle,
    ProjectionPolicy,
)

from .archetypes_v62 import (
    ArchetypeRegistryV62,
    ArchetypeSelectionEngineV62,
    CanonicalIntentEngineV62,
    MultiOutcomeEngineV62,
)
from .decision_support_v62 import (
    AdaptiveProjectionEngineV62,
    ClarificationEngineV62,
    ConfidenceProfileEngineV62,
    PlanningMemoryEngineV62,
    PlanningStyleEngineV62,
    ReflectionGateV62,
    RiskProfileEngineV62,
)
from .intent_graph_v62 import (
    ConstraintPropagationEngineV62,
    DependencyDiscoveryEngineV62,
    IntentGraphEngineV62,
)


class AdaptiveInputProcessingPipelineV62:
    """Provider-free deterministic v6.2 input-processing and planning pipeline."""

    def __init__(
        self,
        *,
        registry: ArchetypeRegistryV62 | None = None,
        projection_policy: ProjectionPolicy | None = None,
    ) -> None:
        self.registry = registry or ArchetypeRegistryV62()
        self.canonical_intent = CanonicalIntentEngineV62()
        self.multi_outcome = MultiOutcomeEngineV62()
        self.archetype_selection = ArchetypeSelectionEngineV62(self.registry)
        self.dependency_discovery = DependencyDiscoveryEngineV62()
        self.constraint_propagation = ConstraintPropagationEngineV62()
        self.intent_graph = IntentGraphEngineV62(self.registry)
        self.confidence = ConfidenceProfileEngineV62()
        self.memory = PlanningMemoryEngineV62()
        self.risk = RiskProfileEngineV62()
        self.clarification = ClarificationEngineV62()
        self.projection = AdaptiveProjectionEngineV62(projection_policy)
        self.reflection = ReflectionGateV62()
        self.style = PlanningStyleEngineV62()

    def process(
        self,
        raw_input: str,
        *,
        planning_style: PlanningStyle = PlanningStyle.CONCISE,
        planning_memory: tuple[PlanningMemoryEntry, ...] = (),
    ) -> EnhancedReasoningPackageV62:
        canonical = self.canonical_intent.canonicalize(raw_input)
        outcomes = self.multi_outcome.recognize(canonical)
        selection = self.archetype_selection.select(canonical)
        archetype = self.registry.get(selection.archetype_id)
        primary_node_id = self.intent_graph.primary_node_id(outcomes)
        dependencies = self.dependency_discovery.discover(
            canonical,
            archetype,
            primary_node_id,
        )
        affected_business_nodes = (
            primary_node_id,
            *(
                f"node-current-{index}-{canonical.semantic_fingerprint[:10]}"
                for index in range(1, len(archetype.current_checkpoint_templates) + 1)
            ),
        )
        constraint_result = self.constraint_propagation.propagate(
            canonical,
            tuple(affected_business_nodes),
        )
        graph = self.intent_graph.build(
            canonical,
            outcomes,
            selection,
            dependencies,
            constraint_result,
        )
        confidence = self.confidence.evaluate(
            canonical,
            outcomes,
            selection,
            graph,
            dependencies,
            constraint_result,
        )
        memory_entry_ids = self.memory.consult(
            planning_memory,
            selection.archetype_id,
        )
        classification, destination, responsibility, workstream = self._metadata(
            selection.confidence,
            confidence.execution_eligible,
        )
        risk = self.risk.evaluate(
            canonical,
            graph,
            dependencies,
            constraint_result,
        )
        clarification = self.clarification.decide(
            outcomes,
            dependencies,
            constraint_result,
            confidence,
            risk,
        )
        preliminary_projection = self.projection.project(
            graph,
            confidence,
            constraint_result,
            risk,
            clarification,
        )
        reflection = self.reflection.evaluate(
            graph,
            preliminary_projection,
            constraint_result,
            classification=classification,
            destination=destination,
            responsibility_domain=responsibility,
            workstream=workstream,
        )
        projection = (
            preliminary_projection
            if reflection.passed and not reflection.review_required
            else self.projection.project(
                graph,
                confidence,
                constraint_result,
                risk,
                clarification,
                reflection_blocked=True,
            )
        )
        checkpoints = tuple(
            node.title
            for node in graph.nodes
            if node.node_id in projection.projected_node_ids
            and node.node_type.value == "current_checkpoint"
        )
        summary = self.style.summarize(
            planning_style,
            outcomes.primary.text,
            checkpoints,
            risk,
            clarification,
        )
        requires_human_decision = clarification.status in {
            ClarificationStatus.REQUIRED,
            ClarificationStatus.HUMAN_REVIEW_REQUIRED,
        }
        values: dict[str, Any] = {
            "contract_version": 5,
            "contract_kind": ContractKind.REASONING.value,
            "source_component": "engines.input_pipeline_v62",
            "canonical_intent": canonical.model_dump(mode="json"),
            "outcomes": outcomes.model_dump(mode="json"),
            "archetype_selection": selection.model_dump(mode="json"),
            "intent_graph": graph.model_dump(mode="json"),
            "dependencies": [item.model_dump(mode="json") for item in dependencies],
            "constraint_result": constraint_result.model_dump(mode="json"),
            "confidence_profile": confidence.model_dump(mode="json"),
            "risk_profile": risk.model_dump(mode="json"),
            "clarification": clarification.model_dump(mode="json"),
            "reflection": reflection.model_dump(mode="json"),
            "planning_style": planning_style.value,
            "memory_entry_ids": memory_entry_ids,
            "projection": projection.model_dump(mode="json"),
            "user_facing_summary": summary,
            "provider_writes": 0,
            "execution_authorized": False,
            "architecture_version": "6.2",
            "classification": classification,
            "destination": destination,
            "responsibility_domain": responsibility,
            "workstream": workstream,
            "planning_model": selection.archetype_id,
            "planning_model_confidence": selection.confidence,
            "requires_human_decision": requires_human_decision,
        }
        return EnhancedReasoningPackageV62(
            canonical_intent=canonical,
            outcomes=outcomes,
            archetype_selection=selection,
            intent_graph=graph,
            dependencies=dependencies,
            constraint_result=constraint_result,
            confidence_profile=confidence,
            risk_profile=risk,
            clarification=clarification,
            reflection=reflection,
            planning_style=planning_style,
            memory_entry_ids=memory_entry_ids,
            projection=projection,
            user_facing_summary=summary,
            classification=classification,
            destination=destination,
            responsibility_domain=responsibility,
            workstream=workstream,
            planning_model=selection.archetype_id,
            planning_model_confidence=selection.confidence,
            requires_human_decision=requires_human_decision,
            package_digest=deterministic_digest(values),
        )

    @staticmethod
    def _metadata(
        selection_confidence: float,
        execution_eligible: bool,
    ) -> tuple[str, str, str, str]:
        if selection_confidence >= 0.85 and execution_eligible:
            return (
                "project",
                "portfolio_projects",
                "project_delivery",
                "Active Projects",
            )
        return (
            "needs_clarification",
            "universal_inbox",
            "unresolved",
            "Needs Clarification",
        )
