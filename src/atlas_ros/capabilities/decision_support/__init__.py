"""Decision-support capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import DecisionSupportResult
from atlas_ros.contracts.reasoning import IntentGraph

CAPABILITY_ID = "atlas.decision-support"


class DecisionSupportPort(Protocol):
    def evaluate(self, graph: IntentGraph) -> DecisionSupportResult: ...


__all__ = ["CAPABILITY_ID", "DecisionSupportPort", "DecisionSupportResult"]
