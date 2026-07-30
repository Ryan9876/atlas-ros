"""Deterministic task-update lifecycle normalization.

The normalizer recognizes only narrow, explicit lifecycle evidence. It produces a
proposal for the existing attended command lifecycle and never authorizes or
performs provider writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts.advisory_v1 import (
    ConfidenceAssessment,
    ProvenanceRecord,
    ValueOrigin,
)
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandType,
    AtlasCommandV1,
    CommandSourceRefV1,
    NormalizedOperationalRecordV1,
    OperationalSnapshotV1,
    TaskUpdateLifecycleNormalizationV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy

_FIELD_RE = re.compile(
    r"(?im)^\s*(?P<key>expected outcome|outcome|done when|done-when|completion criteria|"
    r"delegate due|delegated due|delivery due|follow up|follow-up|checkpoint)\s*:\s*"
    r"(?P<value>[^\n]+?)\s*$"
)
_PERSON_DUE_FIELD_RE = re.compile(
    r"(?im)^\s*(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})\s+due\s*:\s*"
    r"(?P<value>[^\n]+?)\s*$"
)
_FOLLOW_UP_INLINE_RE = re.compile(
    r"(?i)\bfollow\s+up\s+(?P<date>monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|today|tomorrow|next\s+week|next\s+month|\d{4}-\d{2}-\d{2})\b"
)
_WAITING_RE = re.compile(
    r"(?i)\bwaiting\s+(?:for|on)\s+(?P<subject>[^.\n;]+)"
)
_BLOCKED_RE = re.compile(r"(?i)\bblocked\b(?:\s+by\s+(?P<subject>[^.\n;]+))?")
_COMPLETE_RE = re.compile(
    r"(?i)\b(?:completed|is complete|finished|is finished|done)\b"
)
_TENTATIVE_RE = re.compile(
    r"(?i)\b(?:may|might|could|possibly|perhaps|may be able to|might be able to)\b"
)
_DELEGATION_PATTERNS = (
    re.compile(
        r"(?i)(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})\s+"
        r"(?:is\s+handling|owns\s+(?:this|the)?|is\s+responsible\s+for)\s+"
        r"(?P<outcome>[^.\n;]+)"
    ),
    re.compile(
        r"(?i)\b(?:delegated|assigned)\s+to\s+"
        r"(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})"
        r"(?:\s*[:,-]\s*|\s+to\s+)?(?P<outcome>[^.\n;]*)"
    ),
    re.compile(
        r"(?i)\b(?:delegated|assigned)\s+(?P<outcome>[^.\n;]+?)\s+to\s+"
        r"(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})\b"
    ),
)
_DELEGATE_DUE_INLINE_RE = re.compile(
    r"(?i)\b(?:should|must|is expected to|will)\s+(?:finish|complete|deliver)\s+"
    r"(?P<date>[^.\n;,]+)"
)
_GENERIC_DATE_RE = re.compile(
    r"(?i)\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|next\s+week|next\s+month|\d{4}-\d{2}-\d{2})\b"
)


@dataclass(frozen=True, slots=True)
class TaskUpdateLifecycleNormalizer:
    """Normalize natural task updates into existing typed lifecycle commands."""

    policy: OperationalAwarenessPolicy

    def normalize(
        self,
        source: CommandSourceRefV1,
        snapshot: OperationalSnapshotV1,
    ) -> TaskUpdateLifecycleNormalizationV1:
        source_record = self._resolve_source_record(source, snapshot)
        text = source.source_command_text.strip()
        fields = self._extract_fields(text)
        inline_follow_up = _FOLLOW_UP_INLINE_RE.search(text)
        if "follow-up" not in fields and inline_follow_up is not None:
            fields["follow-up"] = self._clean(inline_follow_up.group("date"))
        provenance = (
            ProvenanceRecord(
                source_ref=(
                    f"{source.source_provider.value}:{source.source_task_id}:"
                    f"{source.source_task_revision}"
                ),
                origin=ValueOrigin.OBSERVED,
                observed_at=source.source_task_revision,
            ),
        )

        tentative = bool(_TENTATIVE_RE.search(text))
        waiting = _WAITING_RE.search(text)
        blocked = _BLOCKED_RE.search(text)
        complete = _COMPLETE_RE.search(text)
        delegation = None if tentative else self._delegation_match(text)

        classification = AtlasCommandType.UPDATE
        actionable = False
        responsible: str | None = None
        accountable = source_record.accountable_party or source_record.owner or "Ryan"
        expected: str | None = None
        criteria: tuple[str, ...] = ()
        delegate_due = fields.get("delegate-due")
        follow_up = fields.get("follow-up")
        evidence: list[str] = []
        ambiguity: list[str] = []
        blockers: list[str] = []
        subject: str | None = None

        if waiting is not None:
            classification = AtlasCommandType.WAITING_ON
            actionable = True
            subject = self._clean(waiting.group("subject"))
            evidence.append(f"waiting evidence: {waiting.group(0).strip()}")
        elif blocked is not None:
            classification = AtlasCommandType.BLOCKED
            actionable = True
            subject = self._clean(blocked.group("subject") or source_record.title)
            evidence.append(f"blocked evidence: {blocked.group(0).strip()}")
        elif delegation is not None:
            classification = AtlasCommandType.DELEGATE
            actionable = True
            responsible = self._clean_person(delegation.group("person"))
            expected = fields.get("outcome") or self._clean_outcome(
                delegation.groupdict().get("outcome") or ""
            )
            criteria_text = fields.get("done-when")
            criteria = (criteria_text,) if criteria_text else ()
            inline_due = _DELEGATE_DUE_INLINE_RE.search(text)
            if not criteria and inline_due is not None and expected:
                criteria = (f"{expected} is complete",)
            if delegate_due is None and inline_due is not None:
                delegate_due = self._clean(inline_due.group("date"))
                evidence.append(f"delegate due evidence: {inline_due.group(0).strip()}")
            if responsible is None:
                ambiguity.append("responsible party is not uniquely identifiable")
                blockers.append("Responsible party required")
            if not expected:
                ambiguity.append("expected outcome is missing")
                blockers.append("Expected outcome required")
            if not criteria:
                ambiguity.append("completion criteria are missing")
                blockers.append("Completion criteria required")
            evidence.append(f"ownership evidence: {delegation.group(0).strip()}")
        elif complete is not None:
            classification = AtlasCommandType.COMPLETE
            actionable = True
            subject = source_record.title
            evidence.append(f"completion evidence: {complete.group(0).strip()}")
        elif tentative:
            ambiguity.append("ownership language is tentative")
            blockers.append("Tentative ownership does not establish delegation")
        else:
            blockers.append("No actionable lifecycle transition")

        if classification == AtlasCommandType.DELEGATE:
            unlabeled_dates = self._unlabeled_dates(
                text,
                delegate_due=delegate_due,
                follow_up=follow_up,
            )
            if unlabeled_dates:
                ambiguity.append("date meaning is ambiguous")
                blockers.append("Clarify whether the date is delegate due or Ryan follow-up")

        command_fields = self._command_fields(
            fields=fields,
            source=source,
            responsible=responsible,
            accountable=accountable,
            expected=expected,
            criteria=criteria,
            delegate_due=delegate_due,
            follow_up=follow_up,
            actionable=actionable,
            ambiguity=ambiguity,
            blockers=blockers,
        )
        command = AtlasCommandV1.create(
            command_type=classification,
            source=source,
            subject=responsible if classification == AtlasCommandType.DELEGATE else subject,
            fields=command_fields,
        )
        score = self._confidence_score(
            classification=classification,
            actionable=actionable,
            ambiguity=ambiguity,
            blockers=blockers,
        )
        return TaskUpdateLifecycleNormalizationV1.create(
            source=source,
            classification=classification,
            proposed_command=command,
            actionable_transition=actionable,
            responsible_party=responsible,
            accountable_party=accountable,
            expected_outcome=expected,
            completion_criteria=criteria,
            delegate_due=delegate_due,
            follow_up_checkpoint=follow_up,
            confidence=ConfidenceAssessment(
                score=score,
                rationale=(
                    "deterministic task-update evidence satisfied the lifecycle rule"
                    if actionable and not blockers
                    else (
                        "task update failed closed because required evidence "
                        "was absent or ambiguous"
                    )
                ),
            ),
            provenance=provenance,
            evidence=tuple(evidence),
            ambiguity=tuple(dict.fromkeys(ambiguity)),
            blockers=tuple(dict.fromkeys(blockers)),
        )

    @staticmethod
    def _resolve_source_record(
        source: CommandSourceRefV1,
        snapshot: OperationalSnapshotV1,
    ) -> NormalizedOperationalRecordV1:
        candidates = [
            record
            for record in snapshot.normalized_records
            if record.todoist_task_id == source.source_task_id
            or record.record_ref.canonical_record_id == source.source_task_id
        ]
        if len(candidates) != 1:
            raise ValueError("task update source does not resolve uniquely")
        return candidates[0]

    @staticmethod
    def _extract_fields(text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        aliases = {
            "expected outcome": "outcome",
            "outcome": "outcome",
            "done when": "done-when",
            "done-when": "done-when",
            "completion criteria": "done-when",
            "delegate due": "delegate-due",
            "delegated due": "delegate-due",
            "delivery due": "delegate-due",
            "follow up": "follow-up",
            "follow-up": "follow-up",
            "checkpoint": "follow-up",
        }
        for match in _FIELD_RE.finditer(text):
            key = aliases[match.group("key").lower()]
            value = TaskUpdateLifecycleNormalizer._clean(match.group("value"))
            if key in fields and fields[key] != value:
                raise ValueError(f"conflicting task-update field: {key}")
            fields[key] = value
        for match in _PERSON_DUE_FIELD_RE.finditer(text):
            value = TaskUpdateLifecycleNormalizer._clean(match.group("value"))
            if "delegate-due" in fields and fields["delegate-due"] != value:
                raise ValueError("conflicting task-update field: delegate-due")
            fields["delegate-due"] = value
        return fields

    @staticmethod
    def _delegation_match(text: str) -> re.Match[str] | None:
        for pattern in _DELEGATION_PATTERNS:
            match = pattern.search(text)
            if match is not None:
                return match
        return None

    @staticmethod
    def _clean(value: str) -> str:
        return value.strip().strip(" .;,")

    @classmethod
    def _clean_person(cls, value: str) -> str | None:
        person = cls._clean(value)
        if (
            not person
            or not person[0].isupper()
            or re.search(r"(?i)\b(?:and|or)\b|[/&,]", person)
            or person.casefold() in {"someone", "somebody", "team", "tbd", "unassigned"}
        ):
            return None
        return person

    @classmethod
    def _clean_outcome(cls, value: str) -> str | None:
        outcome = cls._clean(value)
        outcome = re.split(
            r"(?i)\s+and\s+(?:should|must|will|is expected to)\s+"
            r"(?:finish|complete|deliver)\b",
            outcome,
            maxsplit=1,
        )[0]
        outcome = re.sub(r"(?i)^(?:this|the)\s+", "", outcome).strip()
        return outcome or None

    @staticmethod
    def _unlabeled_dates(
        text: str,
        *,
        delegate_due: str | None,
        follow_up: str | None,
    ) -> tuple[str, ...]:
        scrubbed = _FIELD_RE.sub("", text)
        scrubbed = _PERSON_DUE_FIELD_RE.sub("", scrubbed)
        scrubbed = _FOLLOW_UP_INLINE_RE.sub("", scrubbed)
        scrubbed = _DELEGATE_DUE_INLINE_RE.sub("", scrubbed)
        found = tuple(match.group(0) for match in _GENERIC_DATE_RE.finditer(scrubbed))
        if not found:
            return ()
        normalized = {item.casefold() for item in found}
        labeled = {
            item.casefold()
            for item in (delegate_due, follow_up)
            if isinstance(item, str) and item
        }
        return () if normalized <= labeled else found

    @staticmethod
    def _command_fields(
        *,
        fields: dict[str, str],
        source: CommandSourceRefV1,
        responsible: str | None,
        accountable: str,
        expected: str | None,
        criteria: tuple[str, ...],
        delegate_due: str | None,
        follow_up: str | None,
        actionable: bool,
        ambiguity: list[str],
        blockers: list[str],
    ) -> dict[str, str]:
        result = dict(fields)
        values = {
            "responsible": responsible,
            "accountable": accountable,
            "outcome": expected,
            "done-when": criteria[0] if criteria else None,
            "delegate-due": delegate_due,
            "follow-up": follow_up,
            "intent-origin": "task-update",
            "source-update": source.source_command_text,
            "provenance-source-digest": source.source_digest,
            "normalization-actionable": "true" if actionable else "false",
            "normalization-ambiguity": " | ".join(ambiguity) if ambiguity else None,
            "normalization-blockers": " | ".join(blockers) if blockers else None,
        }
        for key, value in values.items():
            if value:
                result[key] = value
        return result

    @staticmethod
    def _confidence_score(
        *,
        classification: AtlasCommandType,
        actionable: bool,
        ambiguity: list[str],
        blockers: list[str],
    ) -> float:
        if ambiguity or blockers:
            return 0.0 if not actionable else 0.4
        if classification == AtlasCommandType.DELEGATE:
            return 1.0
        if actionable:
            return 0.95
        return 0.0
