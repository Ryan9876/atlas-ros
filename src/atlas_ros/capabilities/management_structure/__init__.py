"""Management structure capability boundary for Atlas ROS v7."""

from atlas_ros.capabilities.interfaces import (
    ManagementStructurePort,
    ManagementStructureResult,
)

CAPABILITY_ID = "atlas.management-structure"

__all__ = ["CAPABILITY_ID", "ManagementStructurePort", "ManagementStructureResult"]
