"""Historical v6 capability imports retained only for explicit migration tests.

The v7 production runtime must not import this module. It exists so immutable v6
compatibility expectations can be evaluated without keeping legacy symbols in the
canonical ``atlas_ros.capabilities`` barrel.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

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

__all__ = sorted(_LEGACY_EXPORTS)


def __getattr__(name: str) -> Any:
    """Load one historical symbol only when a migration caller requests it."""
    try:
        module_name, symbol = _LEGACY_EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name), symbol)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
