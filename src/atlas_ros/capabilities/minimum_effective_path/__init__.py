"""Minimum-effective-path planning for Atlas ROS v7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atlas_ros.capabilities.interfaces import MinimumEffectivePathResult
from atlas_ros.contracts.digests import sha256_digest

CAPABILITY_ID = "atlas.minimum-effective-path"


class MinimumEffectivePathPort(Protocol):
    def plan(
        self,
        candidate_step_ids: tuple[str, ...],
        mandatory_step_ids: tuple[str, ...],
    ) -> MinimumEffectivePathResult: ...


@dataclass(frozen=True, slots=True)
class DeterministicMinimumEffectivePathService:
    """Retain mandatory controls and the shortest ordered executable path."""

    capability_id: str = CAPABILITY_ID

    def plan(
        self,
        candidate_step_ids: tuple[str, ...],
        mandatory_step_ids: tuple[str, ...],
    ) -> MinimumEffectivePathResult:
        candidates = tuple(dict.fromkeys(item for item in candidate_step_ids if item))
        mandatory = tuple(dict.fromkeys(item for item in mandatory_step_ids if item))
        candidate_set = set(candidates)
        blockers = tuple(
            f"missing_mandatory_step:{step_id}"
            for step_id in mandatory
            if step_id not in candidate_set
        )
        ordered = tuple(
            dict.fromkeys(
                [*mandatory, *(item for item in candidates if item not in set(mandatory))]
            )
        )
        required_evidence = tuple(f"evidence:{step_id}" for step_id in ordered)
        digest = sha256_digest(
            {
                "step_ids": ordered,
                "required_evidence": required_evidence,
                "blockers": blockers,
            }
        )
        return MinimumEffectivePathResult(
            step_ids=ordered,
            required_evidence=required_evidence,
            blockers=blockers,
            digest=digest,
        )


__all__ = [
    "CAPABILITY_ID",
    "DeterministicMinimumEffectivePathService",
    "MinimumEffectivePathPort",
    "MinimumEffectivePathResult",
]
