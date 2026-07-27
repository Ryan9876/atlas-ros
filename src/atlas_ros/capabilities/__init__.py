"""Canonical capability registry with lazy compatibility exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from atlas_ros.capabilities.compiler import (
    CapabilityCompilationError,
    compile_capability_registry,
)
from atlas_ros.capabilities.registry import CapabilityDescriptor, CapabilityRegistry

if TYPE_CHECKING:
    from atlas_ros.capture import CaptureService
    from atlas_ros.engines import (
        ClassificationExplainability,
        KnowledgeCompositionEngine,
        ManagementReasoningEngine,
        ManagementStructureEngine,
        ManagerIntentInferer,
        ResponsibilityClassifier,
    )
    from atlas_ros.models import (
        KnowledgeDependencyResolver,
        KnowledgeModuleRegistry,
        PlanningModelRegistry,
        load_default_registries,
    )
    from atlas_ros.orchestration import ExecutionCommandFactory, ExecutionOrchestratorV2
    from atlas_ros.planning import (
        DecompositionService,
        DuplicateAnalyzer,
        ExecutionCandidateExtractor,
        ExecutionPlanner,
        ExistingRepresentationMatcher,
        ProgressiveHorizonPolicy,
    )
    from atlas_ros.reconciliation import CanonicalReconciliationService
    from atlas_ros.services import (
        ExecutionReconciliationService,
        RecordRoutingService,
        RoutingService,
        TodoistService,
    )

_LEGACY_EXPORTS: dict[str, tuple[str, str]] = {
    "CaptureService": ("atlas_ros.capture", "CaptureService"),
    "ClassificationExplainability": (
        "atlas_ros.engines",
        "ClassificationExplainability",
    ),
    "KnowledgeCompositionEngine": (
        "atlas_ros.engines",
        "KnowledgeCompositionEngine",
    ),
    "ManagementReasoningEngine": ("atlas_ros.engines", "ManagementReasoningEngine"),
    "ManagementStructureEngine": ("atlas_ros.engines", "ManagementStructureEngine"),
    "ManagerIntentInferer": ("atlas_ros.engines", "ManagerIntentInferer"),
    "ResponsibilityClassifier": ("atlas_ros.engines", "ResponsibilityClassifier"),
    "KnowledgeDependencyResolver": (
        "atlas_ros.models",
        "KnowledgeDependencyResolver",
    ),
    "KnowledgeModuleRegistry": ("atlas_ros.models", "KnowledgeModuleRegistry"),
    "PlanningModelRegistry": ("atlas_ros.models", "PlanningModelRegistry"),
    "load_default_registries": ("atlas_ros.models", "load_default_registries"),
    "ExecutionCommandFactory": (
        "atlas_ros.orchestration",
        "ExecutionCommandFactory",
    ),
    "ExecutionOrchestratorV2": (
        "atlas_ros.orchestration",
        "ExecutionOrchestratorV2",
    ),
    "DecompositionService": ("atlas_ros.planning", "DecompositionService"),
    "DuplicateAnalyzer": ("atlas_ros.planning", "DuplicateAnalyzer"),
    "ExecutionCandidateExtractor": (
        "atlas_ros.planning",
        "ExecutionCandidateExtractor",
    ),
    "ExecutionPlanner": ("atlas_ros.planning", "ExecutionPlanner"),
    "ExistingRepresentationMatcher": (
        "atlas_ros.planning",
        "ExistingRepresentationMatcher",
    ),
    "ProgressiveHorizonPolicy": (
        "atlas_ros.planning",
        "ProgressiveHorizonPolicy",
    ),
    "CanonicalReconciliationService": (
        "atlas_ros.reconciliation",
        "CanonicalReconciliationService",
    ),
    "ExecutionReconciliationService": (
        "atlas_ros.services",
        "ExecutionReconciliationService",
    ),
    "RecordRoutingService": ("atlas_ros.services", "RecordRoutingService"),
    "RoutingService": ("atlas_ros.services", "RoutingService"),
    "TodoistService": ("atlas_ros.services", "TodoistService"),
}

__all__ = [
    "CapabilityCompilationError",
    "CapabilityDescriptor",
    "CapabilityRegistry",
    "CanonicalReconciliationService",
    "CaptureService",
    "ClassificationExplainability",
    "DecompositionService",
    "DuplicateAnalyzer",
    "ExecutionCandidateExtractor",
    "ExecutionCommandFactory",
    "ExecutionOrchestratorV2",
    "ExecutionPlanner",
    "ExecutionReconciliationService",
    "ExistingRepresentationMatcher",
    "KnowledgeCompositionEngine",
    "KnowledgeDependencyResolver",
    "KnowledgeModuleRegistry",
    "ManagementReasoningEngine",
    "ManagementStructureEngine",
    "ManagerIntentInferer",
    "PlanningModelRegistry",
    "ProgressiveHorizonPolicy",
    "RecordRoutingService",
    "ResponsibilityClassifier",
    "RoutingService",
    "TodoistService",
    "compile_capability_registry",
    "load_default_registries",
]


def __getattr__(name: str) -> Any:
    """Load inherited capability exports only when a caller requests one."""
    try:
        module_name, symbol = _LEGACY_EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name), symbol)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
