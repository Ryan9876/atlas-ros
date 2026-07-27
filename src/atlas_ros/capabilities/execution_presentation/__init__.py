"""Human-readable execution presentation capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import ExecutionPresentationResult
from atlas_ros.contracts.execution.pipeline import PipelineRunEnvelope

CAPABILITY_ID = "atlas.execution-presentation"


class ExecutionPresentationPort(Protocol):
    def render(self, envelope: PipelineRunEnvelope) -> ExecutionPresentationResult: ...


__all__ = ["CAPABILITY_ID", "ExecutionPresentationPort", "ExecutionPresentationResult"]
