"""Provider-neutral read boundaries for operational-awareness evidence."""
from __future__ import annotations

from typing import Protocol

from atlas_ros.contracts.operational_awareness import (
    EvidenceConflictV1,
    NormalizedOperationalRecordV1,
)


class OperationalStateReadPort(Protocol):
    """Read authorized operational records without planning or provider writes."""

    def read_records(self, *, scope: str) -> tuple[NormalizedOperationalRecordV1, ...]: ...

    def authority_identities(self) -> tuple[str, ...]: ...

    def missing_sources(self) -> tuple[str, ...]: ...

    def contradictions(self) -> tuple[EvidenceConflictV1, ...]: ...


class ProviderReceiptReadPort(Protocol):
    """Read provider transaction evidence without changing provider state."""

    def read_receipt_records(self, *, scope: str) -> tuple[NormalizedOperationalRecordV1, ...]: ...
