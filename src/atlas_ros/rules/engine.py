from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from atlas_ros.domain.models import Finding, Severity

Predicate = Callable[[Any], bool]
Evidence = Callable[[Any], dict[str, str]]


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    name: str
    description: str
    policy_source: str
    domain: str
    severity: Severity
    applies_to: type[Any]
    predicate: Predicate
    remediation: str
    evidence: Evidence = lambda _: {}
    automation_eligible: bool = False

    def evaluate(self, value: Any, object_id: str) -> Finding | None:
        if not isinstance(value, self.applies_to):
            return None
        if self.predicate(value):
            return None
        return Finding(
            id=f"{self.id}:{object_id}",
            rule_id=self.id,
            severity=self.severity,
            authority="policy",
            affected_object=object_id,
            message=self.description,
            evidence=self.evidence(value),
            recommended_action=self.remediation,
        )


class RulesEngine:
    def __init__(self, rules: Iterable[Rule]) -> None:
        self._rules = tuple(rules)

    def evaluate(
        self, value: Any, object_id: str, *, domains: set[str] | None = None
    ) -> list[Finding]:
        return [
            finding
            for rule in self._rules
            if domains is None or rule.domain in domains
            if (finding := rule.evaluate(value, object_id)) is not None
        ]

    def batch(self, objects: Iterable[tuple[Any, str]]) -> list[Finding]:
        return [finding for value, oid in objects for finding in self.evaluate(value, oid)]
