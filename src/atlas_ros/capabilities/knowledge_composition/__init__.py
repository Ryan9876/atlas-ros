"""Knowledge composition capability boundary for Atlas ROS v7."""

from atlas_ros.capabilities.interfaces import (
    KnowledgeCompositionPort,
    KnowledgeCompositionResult,
)

CAPABILITY_ID = "atlas.knowledge-composition"

__all__ = ["CAPABILITY_ID", "KnowledgeCompositionPort", "KnowledgeCompositionResult"]
