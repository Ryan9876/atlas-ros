"""Application use-case coordination layer."""

from atlas_ros.application.canonical_processing import CanonicalProcessingCoordinator
from atlas_ros.application.execution import AttendedExecutionService, ExecutionBoundaryError

__all__ = [
    "AttendedExecutionService",
    "CanonicalProcessingCoordinator",
    "ExecutionBoundaryError",
]
