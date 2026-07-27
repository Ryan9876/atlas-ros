"""Provider-free shared advisory contracts for Atlas ROS v6.5.

These contracts describe evidence-backed advice only. They grant no provider,
planning, authorization, or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from typing import Mapping, Sequence


class ValueOrigin(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CONFIGURED = "configured"
    SIMULATED = "simulated"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source_ref: str
    origin: ValueOrigin
    observed_at: str | None = None
    schema_version: str = "advisory-v1"


@dataclass(frozen=True, slots=True)
class Assumption:
    statement: str
    material: bool
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class MissingDataIndicator:
    field_name: str
    reason: str
    material: bool = False


@dataclass(frozen=True, slots=True)
class UncertaintyRange:
    low: float | None
    high: float | None
    unit: str
    origin: ValueOrigin = ValueOrigin.UNKNOWN

    def __post_init__(self) -> None:
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("uncertainty low must not exceed high")


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    score: float | None
    rationale: str
    missing_data: tuple[MissingDataIndicator, ...] = ()

    def __post_init__(self) -> None:
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("confidence score must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class AdvisoryAlternative:
    identifier: str
    summary: str
    tradeoffs: tuple[str, ...]
    provenance: tuple[ProvenanceRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class AdvisoryRecommendation:
    identifier: str
    summary: str
    rationale: str
    confidence: ConfidenceAssessment
    alternatives: tuple[AdvisoryAlternative, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    missing_data: tuple[MissingDataIndicator, ...] = ()
    provenance: tuple[ProvenanceRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class AdvisoryReceipt:
    recommendation_id: str
    input_digest: str
    recommendation_digest: str
    schema_version: str = "advisory-v1"


def stable_advisory_digest(
    payload: Mapping[str, object],
    *,
    excluded_keys: Sequence[str] = (),
) -> str:
    """Return a deterministic digest without concealing excluded fields."""

    excluded = set(excluded_keys)
    canonical = {key: value for key, value in sorted(payload.items()) if key not in excluded}
    return sha256(
        dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
