"""Minimum-effective-path capability boundary for Atlas ROS v7."""

from typing import Protocol

from atlas_ros.capabilities.interfaces import MinimumEffectivePathResult

CAPABILITY_ID = "atlas.minimum-effective-path"


class MinimumEffectivePathPort(Protocol):
    def plan(
        self,
        candidate_step_ids: tuple[str, ...],
        mandatory_step_ids: tuple[str, ...],
    ) -> MinimumEffectivePathResult: ...


__all__ = ["CAPABILITY_ID", "MinimumEffectivePathPort", "MinimumEffectivePathResult"]
