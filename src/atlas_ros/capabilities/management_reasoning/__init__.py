"""Management reasoning capability boundary for Atlas ROS v7."""

from atlas_ros.capabilities.interfaces import (
    ManagementReasoningPort,
    ManagementReasoningResult,
)

CAPABILITY_ID = "atlas.management-reasoning"

__all__ = ["CAPABILITY_ID", "ManagementReasoningPort", "ManagementReasoningResult"]
