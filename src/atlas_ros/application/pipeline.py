"""Canonical provider-neutral v7 pipeline through proposed execution planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from atlas_ros.application.canonical_processing import CanonicalProcessingCoordinator
from atlas_ros.capabilities.classification import DeterministicClassificationService
from atlas_ros.capabilities.decision_support import ExplicitDecisionSupportService
from atlas_ros.capabilities.execution_planning import ExecutionPlanningService
from atlas_ros.capabilities.execution_presentation import (
    HumanReadableExecutionPresentationService,
)
from atlas_ros.capabilities.framework_composition import (
    GovernedFrameworkCompositionService,
)
from atlas_ros.capabilities.input_processing import DeterministicInputProcessor
from atlas_ros.capabilities.interfaces import (
    ClassificationResult,
    DecisionSupportResult,
    ExecutionPresentationResult,
    FrameworkCompositionResult,
    KnowledgeCompositionResult,
    ManagementReasoningResult,
    ManagementStructureResult,
    MinimumEffectivePathResult,
    RoutingDecision,
    ScenarioAnalysisResult,
)
from atlas_ros.capabilities.knowledge_composition import (
    DeterministicKnowledgeCompositionService,
)
from atlas_ros.capabilities.management_reasoning import (
    DeterministicManagementReasoningService,
)
from atlas_ros.capabilities.management_structure import (
    DeterministicManagementStructureService,
)
from atlas_ros.capabilities.minimum_effective_path import (
    DeterministicMinimumEffectivePathService,
)
from atlas_ros.capabilities.record_routing import DeterministicRecordRoutingService
from atlas_ros.capabilities.scenario_intelligence import (
    ImmutableScenarioIntelligenceService,
)
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope, PipelineRunEnvelope
from atlas_ros.contracts.execution.transaction import (
    PlannedProviderOperation,
    ProposedExecutionPlan,
)
from atlas_ros.contracts.reasoning import IntentGraph


class CanonicalPipelineError(ValueError):
    """Raised when a stage receives incomplete or contradictory canonical state."""


@dataclass(frozen=True, slots=True)
class CanonicalPipelineState:
    """Immutable provider-neutral state carried between canonical capability stages."""

    envelope: CaptureEnvelope
    provider_requests: tuple[PlannedProviderOperation, ...] = ()
    framework_rules: tuple[str, ...] = ()
    mandatory_step_ids: tuple[str, ...] = ()
    scenario_ids: tuple[str, ...] = ()
    graph: IntentGraph | None = None
    classification: ClassificationResult | None = None
    knowledge: KnowledgeCompositionResult | None = None
    management_reasoning: ManagementReasoningResult | None = None
    management_structure: ManagementStructureResult | None = None
    routing: RoutingDecision | None = None
    framework: FrameworkCompositionResult | None = None
    minimum_effective_path: MinimumEffectivePathResult | None = None
    decision_support: DecisionSupportResult | None = None
    scenario_analysis: ScenarioAnalysisResult | None = None
    proposed_plan: ProposedExecutionPlan | None = None

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        """Return a deterministic digestable representation used for stage lineage."""
        del mode
        return {
            "envelope": self.envelope.model_dump(mode="json"),
            "provider_requests": [item.model_dump(mode="json") for item in self.provider_requests],
            "framework_rules": list(self.framework_rules),
            "mandatory_step_ids": list(self.mandatory_step_ids),
            "scenario_ids": list(self.scenario_ids),
            "graph": self.graph.model_dump(mode="json") if self.graph else None,
            "classification": asdict(self.classification) if self.classification else None,
            "knowledge": asdict(self.knowledge) if self.knowledge else None,
            "management_reasoning": (
                asdict(self.management_reasoning) if self.management_reasoning else None
            ),
            "management_structure": (
                asdict(self.management_structure) if self.management_structure else None
            ),
            "routing": asdict(self.routing) if self.routing else None,
            "framework": asdict(self.framework) if self.framework else None,
            "minimum_effective_path": (
                asdict(self.minimum_effective_path)
                if self.minimum_effective_path
                else None
            ),
            "decision_support": (
                asdict(self.decision_support) if self.decision_support else None
            ),
            "scenario_analysis": (
                asdict(self.scenario_analysis) if self.scenario_analysis else None
            ),
            "proposed_plan": (
                self.proposed_plan.model_dump(mode="json") if self.proposed_plan else None
            ),
        }


@dataclass(frozen=True, slots=True)
class CanonicalPreAuthorizationResult:
    """Complete provider-neutral result with lineage and human-readable evidence."""

    state: CanonicalPipelineState
    lineage: PipelineRunEnvelope
    presentation: ExecutionPresentationResult


@dataclass(frozen=True, slots=True)
class _InputProcessingStage:
    service: DeterministicInputProcessor = DeterministicInputProcessor()
    name: str = "input_processing"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(state, graph=self.service.process(state.envelope))


@dataclass(frozen=True, slots=True)
class _ClassificationStage:
    service: DeterministicClassificationService = DeterministicClassificationService()
    name: str = "classification"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(state, classification=self.service.classify(_graph(state, self.name)))


@dataclass(frozen=True, slots=True)
class _KnowledgeCompositionStage:
    service: DeterministicKnowledgeCompositionService = (
        DeterministicKnowledgeCompositionService()
    )
    name: str = "knowledge_composition"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(state, knowledge=self.service.compose(_graph(state, self.name)))


@dataclass(frozen=True, slots=True)
class _ManagementReasoningStage:
    service: DeterministicManagementReasoningService = (
        DeterministicManagementReasoningService()
    )
    name: str = "management_reasoning"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(
            state,
            management_reasoning=self.service.reason(_graph(state, self.name)),
        )


@dataclass(frozen=True, slots=True)
class _ManagementStructureStage:
    service: DeterministicManagementStructureService = (
        DeterministicManagementStructureService()
    )
    name: str = "management_structure"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        if state.management_reasoning is None:
            raise CanonicalPipelineError("management structure requires management reasoning")
        return replace(
            state,
            management_structure=self.service.structure(state.management_reasoning),
        )


@dataclass(frozen=True, slots=True)
class _RecordRoutingStage:
    service: DeterministicRecordRoutingService = DeterministicRecordRoutingService()
    name: str = "record_routing"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        if state.classification is None or state.management_structure is None:
            raise CanonicalPipelineError(
                "record routing requires classification and management structure"
            )
        return replace(
            state,
            routing=self.service.route(state.classification, state.management_structure),
        )


@dataclass(frozen=True, slots=True)
class _FrameworkCompositionStage:
    service: GovernedFrameworkCompositionService = GovernedFrameworkCompositionService()
    name: str = "framework_composition"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(state, framework=self.service.compose(state.framework_rules))


@dataclass(frozen=True, slots=True)
class _MinimumEffectivePathStage:
    service: DeterministicMinimumEffectivePathService = (
        DeterministicMinimumEffectivePathService()
    )
    name: str = "minimum_effective_path"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        graph = _graph(state, self.name)
        candidates = tuple(
            node.node_id
            for node in graph.nodes
            if node.node_type == "action" and node.execution_candidate
        )
        return replace(
            state,
            minimum_effective_path=self.service.plan(
                candidates,
                state.mandatory_step_ids,
            ),
        )


@dataclass(frozen=True, slots=True)
class _DecisionSupportStage:
    service: ExplicitDecisionSupportService = ExplicitDecisionSupportService()
    name: str = "decision_support"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(
            state,
            decision_support=self.service.evaluate(_graph(state, self.name)),
        )


@dataclass(frozen=True, slots=True)
class _ScenarioIntelligenceStage:
    service: ImmutableScenarioIntelligenceService = ImmutableScenarioIntelligenceService()
    name: str = "scenario_intelligence"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        scenarios = state.scenario_ids or ("current",)
        return replace(state, scenario_analysis=self.service.compare(scenarios))


@dataclass(frozen=True, slots=True)
class _ExecutionPlanningStage:
    service: ExecutionPlanningService = ExecutionPlanningService()
    name: str = "execution_planning"

    def process(self, value: Any) -> CanonicalPipelineState:
        state = _state(value, self.name)
        return replace(
            state,
            proposed_plan=self.service.plan(
                _graph(state, self.name),
                state.provider_requests,
            ),
        )


def canonical_pre_authorization_stages() -> tuple[Any, ...]:
    """Return the sole ordered provider-neutral capability sequence before authorization."""
    return (
        _InputProcessingStage(),
        _ClassificationStage(),
        _KnowledgeCompositionStage(),
        _ManagementReasoningStage(),
        _ManagementStructureStage(),
        _RecordRoutingStage(),
        _FrameworkCompositionStage(),
        _MinimumEffectivePathStage(),
        _DecisionSupportStage(),
        _ScenarioIntelligenceStage(),
        _ExecutionPlanningStage(),
    )


@dataclass(frozen=True, slots=True)
class CanonicalPreAuthorizationPipeline:
    """Execute the sole canonical provider-neutral pipeline before attended authorization."""

    coordinator: CanonicalProcessingCoordinator
    presenter: HumanReadableExecutionPresentationService = (
        HumanReadableExecutionPresentationService()
    )

    def process(
        self,
        envelope: CaptureEnvelope,
        *,
        provider_requests: tuple[PlannedProviderOperation, ...] = (),
        framework_rules: tuple[str, ...] = (),
        mandatory_step_ids: tuple[str, ...] = (),
        scenario_ids: tuple[str, ...] = (),
    ) -> CanonicalPreAuthorizationResult:
        expected = tuple(stage.name for stage in canonical_pre_authorization_stages())
        actual = tuple(stage.name for stage in self.coordinator.stages)
        if actual != expected:
            raise CanonicalPipelineError(
                "coordinator stages do not match the canonical pre-authorization sequence"
            )
        initial = CanonicalPipelineState(
            envelope=envelope,
            provider_requests=provider_requests,
            framework_rules=framework_rules,
            mandatory_step_ids=mandatory_step_ids,
            scenario_ids=scenario_ids,
        )
        value, lineage = self.coordinator.process(envelope, initial_value=initial)
        state = _state(value, "pipeline_completion")
        if state.proposed_plan is None:
            raise CanonicalPipelineError("canonical pipeline did not produce a proposed plan")
        return CanonicalPreAuthorizationResult(
            state=state,
            lineage=lineage,
            presentation=self.presenter.render(lineage),
        )


def _state(value: Any, stage: str) -> CanonicalPipelineState:
    if not isinstance(value, CanonicalPipelineState):
        raise CanonicalPipelineError(f"{stage} requires canonical pipeline state")
    return value


def _graph(state: CanonicalPipelineState, stage: str) -> IntentGraph:
    if state.graph is None:
        raise CanonicalPipelineError(f"{stage} requires an intent graph")
    return state.graph


__all__ = [
    "CanonicalPipelineError",
    "CanonicalPipelineState",
    "CanonicalPreAuthorizationPipeline",
    "CanonicalPreAuthorizationResult",
    "canonical_pre_authorization_stages",
]
