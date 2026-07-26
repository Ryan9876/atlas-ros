from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from atlas_ros.contracts.intent_v1 import InstructionRole, IntentPartitionV1
from atlas_ros.contracts.models import deterministic_digest

_EXPLICIT_OUTCOME = re.compile(
    r"^(?:task|outcome|objective|goal)\s*[:=]\s*(?P<value>.+)$", re.IGNORECASE
)
_PRIMARY_VERBS = {
    "approve",
    "build",
    "create",
    "define",
    "develop",
    "establish",
    "generate",
    "implement",
    "launch",
    "prepare",
    "produce",
    "review",
    "run",
    "start",
}
_CONTROL_EVALUATION = {
    "benchmark",
    "compare",
    "comparison",
    "side-by-side",
    "test",
    "version",
    "v5.2",
    "v5.3",
    "v5.4",
    "v5.5",
    "v5.6",
    "v6",
}
_CONTROL_AUDIT = {
    "audit",
    "checkpoint",
    "digest",
    "hash",
    "journal",
    "readback",
    "receipt",
    "reconcile",
    "reconciliation",
    "transaction",
}
_CONTROL_CONSTRAINT = {
    "do not",
    "don't",
    "duplicate",
    "limit",
    "must not",
    "no overwrite",
    "preserve",
    "prohibit",
    "remain unchanged",
}
_CONDITIONAL_PREFIXES = ("after ", "if ", "once ", "when ")
_DELEGATION_SIGNALS = (
    "delegate ",
    "delegated ",
    "have the technical team ",
    "implementation team ",
    "technical team ",
)


class IntentPartitioner:
    """Deterministically assigns instruction clauses to semantic roles."""

    def __init__(self, *, confidence_threshold: float = 0.80) -> None:
        self._confidence_threshold = confidence_threshold

    def partition(self, text: str, *, correlation_id: UUID) -> IntentPartitionV1:
        clauses = self._clauses(text)
        explicit = [
            match.group("value").strip()
            for clause in clauses
            if (match := _EXPLICIT_OUTCOME.match(clause))
        ]
        ambiguities: list[str] = []
        if len(explicit) > 1:
            ambiguities.append("multiple_explicit_primary_outcomes")

        primary_clause = explicit[0] if explicit else self._select_primary_clause(clauses)
        if not primary_clause:
            ambiguities.append("missing_primary_business_outcome")

        primary_outcome = self._normalize_outcome(primary_clause) if primary_clause else ""
        roles: dict[InstructionRole, list[str]] = defaultdict(list)
        primary_consumed = False
        for clause in clauses:
            explicit_match = _EXPLICIT_OUTCOME.match(clause)
            semantic_clause = explicit_match.group("value").strip() if explicit_match else clause
            if not primary_consumed and primary_clause and semantic_clause == primary_clause:
                roles[InstructionRole.PRIMARY_BUSINESS_OUTCOME].append(clause)
                primary_consumed = True
                continue
            role = self._classify_secondary(semantic_clause)
            roles[role].append(clause)

        non_control_imperatives = [
            clause
            for clause in clauses
            if not _EXPLICIT_OUTCOME.match(clause)
            and self._is_imperative(clause)
            and self._classify_secondary(clause)
            is InstructionRole.CURRENT_BUSINESS_ACTION
        ]
        if not explicit and len(non_control_imperatives) > 1:
            distinct = {self._normalize_text(value) for value in non_control_imperatives}
            if len(distinct) > 1:
                ambiguities.append("multiple_plausible_primary_outcomes")

        confidence = self._confidence(
            explicit=bool(explicit),
            primary=primary_outcome,
            ambiguities=ambiguities,
        )
        if confidence < self._confidence_threshold:
            ambiguities.append("intent_partition_confidence_below_threshold")
        ambiguities = list(dict.fromkeys(ambiguities))
        requires_human_decision = bool(ambiguities)

        arguments = {
            "correlation_id": correlation_id,
            "primary_business_outcome": primary_outcome,
            "current_business_actions": tuple(roles[InstructionRole.CURRENT_BUSINESS_ACTION]),
            "delegated_actions": tuple(roles[InstructionRole.DELEGATED_ACTION]),
            "conditional_actions": tuple(roles[InstructionRole.CONDITIONAL_ACTION]),
            "evaluation_context": tuple(roles[InstructionRole.EVALUATION_CONTEXT]),
            "audit_requirements": tuple(roles[InstructionRole.AUDIT_REQUIREMENT]),
            "execution_constraints": tuple(roles[InstructionRole.EXECUTION_CONSTRAINT]),
            "reference_context": tuple(roles[InstructionRole.REFERENCE_CONTEXT]),
            "source_clauses": {
                role.value: tuple(values)
                for role, values in sorted(
                    roles.items(), key=lambda item: item[0].value
                )
            },
            "confidence": confidence,
            "ambiguities": tuple(ambiguities),
            "requires_human_decision": requires_human_decision,
        }
        unsigned = IntentPartitionV1(partition_digest="0" * 64, **arguments)
        return IntentPartitionV1(
            **arguments,
            partition_digest=deterministic_digest(unsigned.digest_payload()),
        )

    @staticmethod
    def _clauses(text: str) -> tuple[str, ...]:
        normalized = text.replace("\r", "\n")
        lines: list[str] = []
        for raw_line in normalized.split("\n"):
            line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
            if not line:
                continue
            lines.extend(
                item.strip()
                for item in re.split(r"(?<=[.!?])\s+(?=[A-Za-z])", line)
                if item.strip()
            )
        return tuple(dict.fromkeys(lines))

    def _select_primary_clause(self, clauses: Iterable[str]) -> str:
        material = tuple(clauses)
        for clause in material:
            if self._is_imperative(clause) and not self._is_secondary_control_only(clause):
                return clause
        for clause in material:
            if self._is_pilot(clause):
                return clause
        for clause in material:
            if self._is_imperative(clause):
                return clause
        return material[0] if len(material) == 1 else ""

    def _classify_secondary(self, clause: str) -> InstructionRole:
        lowered = clause.casefold().strip()
        if lowered.startswith(_CONDITIONAL_PREFIXES):
            return InstructionRole.CONDITIONAL_ACTION
        if any(signal in lowered for signal in _CONTROL_CONSTRAINT):
            return InstructionRole.EXECUTION_CONSTRAINT
        if any(signal in lowered for signal in _DELEGATION_SIGNALS):
            return InstructionRole.DELEGATED_ACTION
        if any(signal in lowered for signal in _CONTROL_AUDIT):
            return InstructionRole.AUDIT_REQUIREMENT
        if any(signal in lowered for signal in _CONTROL_EVALUATION):
            return InstructionRole.EVALUATION_CONTEXT
        if self._is_imperative(clause):
            return InstructionRole.CURRENT_BUSINESS_ACTION
        return InstructionRole.REFERENCE_CONTEXT

    def _is_secondary_control_only(self, clause: str) -> bool:
        role = self._classify_secondary(clause)
        return role in {
            InstructionRole.EVALUATION_CONTEXT,
            InstructionRole.AUDIT_REQUIREMENT,
            InstructionRole.EXECUTION_CONSTRAINT,
        }

    @staticmethod
    def _is_imperative(clause: str) -> bool:
        first = re.sub(r"[^a-z]+", " ", clause.casefold()).strip().split(" ", 1)[0]
        return first in _PRIMARY_VERBS

    @staticmethod
    def _is_pilot(value: str) -> bool:
        lowered = value.casefold()
        return any(
            signal in lowered
            for signal in (
                " pilot",
                "pilot ",
                "proof of concept",
                "poc",
                "controlled trial",
            )
        )

    def _normalize_outcome(self, value: str) -> str:
        cleaned = value.strip().rstrip(". ")
        cleaned = re.sub(r"^(?:please\s+)?", "", cleaned, flags=re.IGNORECASE)
        lowered = cleaned.casefold()
        audit_primary = (
            lowered.startswith(("produce ", "generate ", "prepare ", "review "))
            and any(token in lowered for token in _CONTROL_AUDIT | {"report"})
        )
        if self._is_pilot(cleaned) and not audit_primary:
            subject = re.sub(
                r"^(?:launch|run|start|establish|create|develop|implement)\s+(?:the\s+)?",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            subject = re.sub(r"^(?:a\s+)?pilot\s+(?:for|of)\s+", "", subject, flags=re.IGNORECASE)
            subject = re.sub(r"\s+pilot$", "", subject, flags=re.IGNORECASE).strip()
            subject = self._canonical_subject(subject)
            return f"Launch the {subject} pilot"
        return cleaned[:1].upper() + cleaned[1:] if cleaned else ""

    @staticmethod
    def _canonical_subject(value: str) -> str:
        subject = " ".join(value.split())
        subject = re.sub(
            r"^automating\s+(.+?)\s+code upgrades$",
            r"\1 code-upgrade automation",
            subject,
            flags=re.IGNORECASE,
        )
        subject = re.sub(r"\barista\b", "Arista", subject, flags=re.IGNORECASE)
        subject = re.sub(r"\bcisco\b", "Cisco", subject, flags=re.IGNORECASE)
        subject = re.sub(r"\bcloud\s*vision\b", "CloudVision", subject, flags=re.IGNORECASE)
        subject = re.sub(r"\bcode[ -]?upgrade\b", "code-upgrade", subject, flags=re.IGNORECASE)
        if subject and subject[0].islower():
            subject = subject[0].upper() + subject[1:]
        return subject

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    @staticmethod
    def _confidence(*, explicit: bool, primary: str, ambiguities: list[str]) -> float:
        if ambiguities:
            return 0.45
        if explicit:
            return 1.0
        if primary:
            return 0.95 if " pilot" in primary.casefold() else 0.85
        return 0.0
