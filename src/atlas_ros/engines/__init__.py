from .archetypes_v62 import ArchetypeRegistryV62, ArchetypeSelectionEngineV62
from .canonical_intent_v62 import CanonicalIntentEngineV62
from .classification_explainability import ClassificationExplainability
from .coherent_management_structure import ManagementStructureEngine
from .decision_support_v62 import (
    AdaptiveProjectionEngineV62,
    ClarificationEngineV62,
    ConfidenceProfileEngineV62,
    PlanningMemoryEngineV62,
    PlanningStyleEngineV62,
    ReflectionGateV62,
    RiskProfileEngineV62,
)
from .domain_knowledge_v62 import DomainKnowledgeRegistryV62
from .input_pipeline_v62 import AdaptiveInputProcessingPipelineV62
from .intent_graph_v62 import (
    ConstraintPropagationEngineV62,
    DependencyDiscoveryEngineV62,
    IntentGraphEngineV62,
)
from .intent_partitioning import IntentPartitioner
from .knowledge_composition import KnowledgeCompositionEngine
from .management_reasoning import ManagementReasoningEngine
from .manager_intent import IntentAssessment, ManagerIntentInferer
from .multi_outcome_v62 import MultiOutcomeEngineV62
from .reasoning_coherence import ReasoningCoherenceGate
from .responsibility_classification import ResponsibilityAssessment, ResponsibilityClassifier

__all__ = [
    "AdaptiveInputProcessingPipelineV62",
    "AdaptiveProjectionEngineV62",
    "ArchetypeRegistryV62",
    "ArchetypeSelectionEngineV62",
    "CanonicalIntentEngineV62",
    "ClarificationEngineV62",
    "ConfidenceProfileEngineV62",
    "ConstraintPropagationEngineV62",
    "DependencyDiscoveryEngineV62",
    "DomainKnowledgeRegistryV62",
    "IntentGraphEngineV62",
    "MultiOutcomeEngineV62",
    "PlanningMemoryEngineV62",
    "PlanningStyleEngineV62",
    "ReflectionGateV62",
    "RiskProfileEngineV62",
    "ClassificationExplainability",
    "IntentAssessment",
    "IntentPartitioner",
    "KnowledgeCompositionEngine",
    "ManagementReasoningEngine",
    "ManagementStructureEngine",
    "ManagerIntentInferer",
    "ReasoningCoherenceGate",
    "ResponsibilityAssessment",
    "ResponsibilityClassifier",
]


# v6.5 provider-free governed execution intelligence
from .governed_execution_v65 import (
    AdvisoryError as AdvisoryError,
    AuthorityTier as AuthorityTier,
    ClaimStateV65 as ClaimStateV65,
    ExecutionStateV65 as ExecutionStateV65,
    FrameworkRuleV65 as FrameworkRuleV65,
    FrameworkCompositionV65 as FrameworkCompositionV65,
    GovernedFrameworkComposerV65 as GovernedFrameworkComposerV65,
    PathStepV65 as PathStepV65,
    MinimumEffectivePathV65 as MinimumEffectivePathV65,
    MinimumEffectivePathPlannerV65 as MinimumEffectivePathPlannerV65,
    ExecutionEventV65 as ExecutionEventV65,
    ExecutionRecordV65 as ExecutionRecordV65,
    PresentationEntryV65 as PresentationEntryV65,
    PresentationV65 as PresentationV65,
    ExecutionPresenterV65 as ExecutionPresenterV65,
    ScenarioV65 as ScenarioV65,
    ScenarioComparisonV65 as ScenarioComparisonV65,
    ScenarioIntelligenceV65 as ScenarioIntelligenceV65,
)

__all__.extend([
    "AdvisoryError",
    "AuthorityTier",
    "ClaimStateV65",
    "ExecutionStateV65",
    "FrameworkRuleV65",
    "FrameworkCompositionV65",
    "GovernedFrameworkComposerV65",
    "PathStepV65",
    "MinimumEffectivePathV65",
    "MinimumEffectivePathPlannerV65",
    "ExecutionEventV65",
    "ExecutionRecordV65",
    "PresentationEntryV65",
    "PresentationV65",
    "ExecutionPresenterV65",
    "ScenarioV65",
    "ScenarioComparisonV65",
    "ScenarioIntelligenceV65",
])
