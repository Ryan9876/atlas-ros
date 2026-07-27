"""Provider-free shared advisory contracts for Atlas ROS v6.5.

These immutable contracts model evidence-backed advice only.  They grant no
provider, planning, authorization, or execution authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum
from hashlib import sha256
from json import dumps
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence


class ValueOrigin(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CONFIGURED = "configured"
    SIMULATED = "simulated"
    UNKNOWN = "unknown"


class AdvisoryValueState(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    PROPOSAL = "proposal"
    APPROVAL = "approval"
    ACTION = "action"


def _canonical(value: object) -> object:
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(
            (_canonical(item) for item in value),
            key=lambda item: dumps(item, sort_keys=True),
        )
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("non-finite values cannot be represented in an advisory digest")
        return value
    if value is None or isinstance(value, str | int | bool):
        return value
    raise TypeError(f"unsupported advisory digest value: {type(value).__name__}")


def stable_advisory_digest(
    payload: Mapping[str, object],
    *,
    excluded_keys: Sequence[str] = (),
) -> str:
    """Return a deterministic digest; excluded fields remain caller-visible."""
    excluded = set(excluded_keys)
    canonical = {
        key: _canonical(value)
        for key, value in sorted(payload.items())
        if key not in excluded
    }
    return sha256(
        dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source_ref: str
    origin: ValueOrigin
    observed_at: str | None = None
    schema_version: str = "advisory-v1"

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("provenance requires source_ref")


@dataclass(frozen=True, slots=True)
class Assumption:
    statement: str
    material: bool
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("assumption requires statement")


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
        if not self.unit.strip():
            raise ValueError("uncertainty requires unit")
        if self.low is not None and not isfinite(self.low):
            raise ValueError("uncertainty low must be finite")
        if self.high is not None and not isfinite(self.high):
            raise ValueError("uncertainty high must be finite")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("uncertainty low must not exceed high")


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    score: float | None
    rationale: str
    missing_data: tuple[MissingDataIndicator, ...] = ()

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError("confidence requires rationale")
        if self.score is not None and (
            not isfinite(self.score) or not 0.0 <= self.score <= 1.0
        ):
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
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    value_state: AdvisoryValueState = AdvisoryValueState.PROPOSAL

    def __post_init__(self) -> None:
        if not all(item.strip() for item in (self.identifier, self.summary, self.rationale)):
            raise ValueError("recommendation requires identifier, summary, and rationale")


@dataclass(frozen=True, slots=True)
class AdvisoryReceipt:
    recommendation_id: str
    input_digest: str
    recommendation_digest: str
    schema_version: str = "advisory-v1"

    def __post_init__(self) -> None:
        if not all(
            item.strip()
            for item in (self.recommendation_id, self.input_digest, self.recommendation_digest)
        ):
            raise ValueError("receipt requires identifiers and digests")

    def verify(self, recommendation: AdvisoryRecommendation, input_payload: Mapping[str, object]) -> bool:
        return (
            self.recommendation_id == recommendation.identifier
            and self.input_digest == stable_advisory_digest(input_payload)
            and self.recommendation_digest
            == stable_advisory_digest({"recommendation": recommendation})
        )


@dataclass(frozen=True, slots=True)
class AdvisoryEnvelope:
    schema_version: str
    recommendation: AdvisoryRecommendation
    receipt: AdvisoryReceipt
    replay_id: str
    metadata: Mapping[str, str] = MappingProxyType({})

    def __post_init__(self) -> None:
        if self.schema_version != "advisory-v1":
            raise ValueError("unsupported advisory schema version")
        if not self.replay_id.strip():
            raise ValueError("advisory envelope requires replay_id")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
