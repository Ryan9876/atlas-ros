"""Provider-free execution intelligence capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import ExecutionIntelligenceResult
from atlas_ros.contracts.execution.transaction import ExecutionTransactionReceipt

CAPABILITY_ID = "atlas.execution-intelligence"


class ExecutionIntelligencePort(Protocol):
    def analyze(
        self,
        receipt: ExecutionTransactionReceipt,
    ) -> ExecutionIntelligenceResult: ...


__all__ = ["CAPABILITY_ID", "ExecutionIntelligencePort", "ExecutionIntelligenceResult"]
