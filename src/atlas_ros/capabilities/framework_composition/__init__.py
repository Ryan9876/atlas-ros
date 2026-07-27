"""Governed framework composition capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import FrameworkCompositionResult

CAPABILITY_ID = "atlas.framework-composition"


class FrameworkCompositionPort(Protocol):
    def compose(self, rules: tuple[str, ...]) -> FrameworkCompositionResult: ...


__all__ = ["CAPABILITY_ID", "FrameworkCompositionPort", "FrameworkCompositionResult"]
