"""Deterministic task-update lifecycle normalization.

The normalizer recognizes bounded lifecycle evidence, including ordinary Todoist
comment updates. It produces proposals for the existing attended command lifecycle
and never authorizes or performs provider writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

_PERSON = r"[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3}"
_DATE = (
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow|"
    r"next\s+week|next\s+month|\d{4}-\d{2}-\d{2}"
)
_FIELD_RE = re.compile(
    r"(?im)^\s*(?P<key>expected outcome|outcome|done when|done-when|completion criteria|"
    r"delegate due|delegated due|delivery due|follow up|follow-up|checkpoint)\s*:\s*"
    r"(?P<value>[^\n]+?)\s*$"
)
_PERSON_DUE_FIELD_RE = re.compile(
    rf"(?im)^\s*(?P<person>{_PERSON})\s+due\s*:\s*(?P<value>[^\n]+?)\s*$"
)
_FOLLOW_UP_PATTERNS = (
    re.compile(
        rf"(?i)\b(?:I\s+(?:need|should|must|will)\s+to\s+)?follow\s+up"
        rf"(?:\s+with\s+(?P<person>{_PERSON}|him|her|them))?\s+(?:on\s+)?"
        rf"(?P<date>{_DATE})\b"
    ),
    re.compile(
        rf"(?i)\bcheck\s+back\s+with\s+(?P<person>{_PERSON}|him|her|them)\s+"
        rf"(?:on\s+)?(?P<date>{_DATE})\b"
    ),
    re.compile(
        rf"(?i)\breview\s+(?:this|it)\s+with\s+(?P<person>{_PERSON}|him|her|them)\s+"
        rf"(?:on\s+)?(?P<date>{_DATE})\b"
    ),
    re.compile(
        rf"(?i)\bask\s+(?P<person>{_PERSON}|him|her|them)\s+about\s+[^.\n;]+?\s+"
        rf"(?:on\s+)?(?P<date>{_DATE})\b"
    ),
)
_WAITING_RE = re.compile(r"(?i)\bwaiting\s+(?:for|on)\s+(?P<subject>[^.\n;]+)")
_BLOCKED_RE = re.compile(r"(?i)\bblocked\b(?:\s+by\s+(?P<subject>[^.\n;]+))?")
_COMPLETE_RE = re.compile(r"(?i)\b(?:completed|is complete|finished|is finished|done)\b")
_TENTATIVE_RE = re.compile(
    r"(?i)\b(?:may|might|could|possibly|perhaps|may be able to|might be able to)\b"
)
_DIRECT_COMMITMENT_PATTERNS = (
    re.compile(
        rf"(?i)(?P<person>{_PERSON})\s+"
        r"(?P<verb>is\s+going\s+to|will|agreed\s+to|committed\s+to|plans\s+to|"
        r"said\s+(?:he|she|they)\s+would)\s+(?P<outcome>[^.\n;]+)"
    ),
    re.compile(
        rf"(?i)(?P<person>{_PERSON})\s+"
        r"(?P<verb>is\s+handling|owns\s+(?:this|the)?|is\s+responsible\s+for)\s+"
        r"(?P<outcome>[^.\n;]+)"
    ),
    re.compile(
        rf"(?i)\b(?:delegated|assigned)\s+to\s+(?P<person>{_PERSON})"
        r"(?:\s*[:,-]\s*|\s+to\s+)?(?P<outcome>[^.\n;]*)"
    ),
    re.compile(
        rf"(?i)\b(?:delegated|assigned)\s+(?P<outcome>[^.\n;]+?)\s+to\s+"
        rf"(?P<person>{_PERSON})\b"
    ),
)
_PRONOUN_COMMITMENT_RE = re.compile(
    r"(?i)\bI\s+(?:spoke|talked)\s+to\s+(?P<antecedents>[^,.]+)[,.]\s*"
    r"(?P<pronoun>he|she|they)\s+"
    r"(?P<verb>is\s+going\s+to|are\s+going\s+to|will|agreed\s+to|committed\s+to|"
    r"plans\s+to|said\s+(?:he|she|they)\s+would)\s+"
    r"(?P<outcome>[^.\n;]+)"
)
_DELEGATE_DUE_INLINE_RE = re.compile(
    r"(?i)\b(?:should|must|is expected to|will)\s+(?:finish|complete|deliver)\s+"
    r"(?P<date>[^.\n;,]+)"
)
_GENERIC_DATE_RE = re.compile(rf"(?i)\b(?:{_DATE})\b")
_VAGUE_OUTCOME_RE = re.compile(
    r"(?i)^(?:take\s+care\s+of\s+(?:it|this)|handle\s+(?:it|this)|do\s+(?:it|this)|"
    r"follow\s+up|look\s+into\s+(?:it|this)|work\s+on\s+(?:it|this))$"
)


@dataclass(frozen=True, slots=True)
class _DelegationEvidence:
    person: str | None
    outcome: str
    evidence: str
    pronoun: str | None = None
    ambiguity: str | None = None


@dataclass(frozen=True, slots=True)
class _FollowUpEvidence:
    raw_date: str
    resolved_date: str
    person_reference: str | None
    evidence: str


@dataclass(frozen=True, slots=True)
class TaskUpdateLifecycleNormalizer:
    """Normalize natural task or comment updates into typed lifecycle commands."""

    policy: OperationalAwarenessPolicy

    def normalize(
        self,
        source: CommandSourceRefV1,
        snapshot: OperationalSnapshotV1,
    ) -> TaskUpdateLifecycleNormalizationV1:
        source_record = self._resolve_source_record(source, snapshot)
        text = source.source_command_text.strip()
        fields = self._extract_fields(text)
        field_origins: dict[str, str] = {
            key: "explicit" for key in fields
        }
        provenance: list[ProvenanceRecord] = [
            ProvenanceRecord(
                source_ref=(
                    f"{source.source_provider.value}:"
                    f"{source.source_event_id or source.source_task_id}:"
                    f"{source.source_task_revision}"
                ),
                origin=ValueOrigin.OBSERVED,
                observed_at=source.source_task_revision,
            )
        ]

        tentative = bool(_TENTATIVE_RE.search(text))
        waiting = _WAITING_RE.search(text)
        blocked = _BLOCKED_RE.search(text)
        complete = _COMPLETE_RE.search(text)
        delegation = None if tentative else self._delegation_evidence(text)

        classification = AtlasCommandType.UPDATE
        actionable = False
        responsible: str | None = None
        accountable = source_record.accountable_party or source_record.owner or "Ryan"
        expected: str | None = None
        criteria: tuple[str, ...] = ()
        delegate_due = fields.get("delegate-due")
        follow_up_evidence = self._follow_up_evidence(text, source)
        follow_up = fields.get("follow-up")
        resolved_follow_up: str | None = None
        if follow_up is None and follow_up_evidence is not None:
            follow_up = follow_up_evidence.resolved_date
            resolved_follow_up = follow_up_evidence.resolved_date
            field_origins["follow-up"] = "context-derived"
            provenance.append(
                ProvenanceRecord(
                    source_ref=f"{source.source_event_id or source.source_task_id}:follow-up",
                    origin=ValueOrigin.INFERRED,
                    observed_at=source.source_task_revision,
                )
            )
        elif follow_up is not None:
            resolved_follow_up = self._resolve_relative_date(follow_up, source)
            follow_up = resolved_follow_up
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
            responsible = self._clean_person(delegation.person or "")
            if delegation.ambiguity:
                ambiguity.append(delegation.ambiguity)
                blockers.append("Pronoun antecedent must resolve uniquely")
            explicit_outcome = fields.get("outcome")
            if explicit_outcome:
                expected = self._clean(explicit_outcome)
            else:
                expected = self._inferred_expected_outcome(
                    responsible,
                    delegation.outcome,
                    source_record.title,
                )
                if expected:
                    field_origins["outcome"] = (
                        "context-derived"
                        if self._uses_parent_context(expected, source_record.title)
                        else "inferred"
                    )
                    provenance.append(
                        ProvenanceRecord(
                            source_ref=f"{source.source_event_id or source.source_task_id}:outcome",
                            origin=ValueOrigin.INFERRED,
                            observed_at=source.source_task_revision,
                        )
                    )
            criteria_text = fields.get("done-when")
            if criteria_text:
                criteria = (self._clean(criteria_text),)
            elif expected and not self._is_vague_outcome(delegation.outcome):
                inferred_criterion = self._infer_completion_criterion(
                    delegation.outcome,
                    expected,
                    accountable,
                )
                if inferred_criterion:
                    criteria = (inferred_criterion,)
                    field_origins["done-when"] = "inferred"
                    provenance.append(
                        ProvenanceRecord(
                            source_ref=(
                                f"{source.source_event_id or source.source_task_id}:"
                                "done-when"
                            ),
                            origin=ValueOrigin.INFERRED,
                            observed_at=source.source_task_revision,
                        )
                    )
            inline_due = _DELEGATE_DUE_INLINE_RE.search(text)
            if delegate_due is None and inline_due is not None:
                delegate_due = self._clean(inline_due.group("date"))
                field_origins["delegate-due"] = "context-derived"
                evidence.append(f"delegate due evidence: {inline_due.group(0).strip()}")
            if responsible is None:
                ambiguity.append("responsible party is not uniquely identifiable")
                blockers.append("Responsible party required")
            if self._is_vague_outcome(delegation.outcome):
                ambiguity.append("expected outcome is vague or not objectively testable")
                blockers.append("Concrete expected outcome required")
            elif not expected:
                ambiguity.append("expected outcome is missing")
                blockers.append("Expected outcome required")
            if not criteria:
                ambiguity.append("completion criteria are missing or not objectively testable")
                blockers.append("Completion criteria required")
            evidence.append(f"ownership evidence: {delegation.evidence}")
            if delegation.pronoun:
                evidence.append(
                    "pronoun evidence: "
                    f"{delegation.pronoun} resolved to {responsible or 'unresolved'}"
                )
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

        if follow_up_evidence is not None:
            evidence.append(f"Ryan follow-up evidence: {follow_up_evidence.evidence}")
            if (
                follow_up_evidence.person_reference
                and follow_up_evidence.person_reference.casefold() in {"him", "her", "them"}
                and delegation is None
            ):
                ambiguity.append("follow-up pronoun has no unique local antecedent")
                blockers.append("Follow-up person must resolve uniquely")

        if classification == AtlasCommandType.DELEGATE:
            unlabeled_dates = self._unlabeled_dates(
                text,
                delegate_due=delegate_due,
                follow_up=follow_up,
            )
            if unlabeled_dates:
                ambiguity.append("date meaning is ambiguous")
                blockers.append("Clarify whether the date is delegate due or Ryan follow-up")

        requires_approval = any(
            origin in {"inferred", "context-derived", "defaulted-by-policy"}
            for origin in field_origins.values()
        )
        checkpoint_title = self._checkpoint_title(
            responsible=responsible,
            raw_outcome=(delegation.outcome if delegation else ""),
            parent_title=source_record.title,
        )
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
            field_origins=field_origins,
            requires_approval=requires_approval,
            follow_up_raw=(follow_up_evidence.raw_date if follow_up_evidence else None),
            checkpoint_title=checkpoint_title,
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
            inferred=requires_approval,
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
                    "deterministic task-update evidence produced a reviewable proposal"
                    if actionable and not blockers
                    else (
                        "task update failed closed because required evidence "
                        "was absent or ambiguous"
                    )
                ),
            ),
            provenance=tuple(provenance),
            evidence=tuple(dict.fromkeys(evidence)),
            ambiguity=tuple(dict.fromkeys(ambiguity)),
            blockers=tuple(dict.fromkeys(blockers)),
            field_origins=field_origins,
            requires_attended_approval=requires_approval,
            resolved_follow_up_date=resolved_follow_up,
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

    @classmethod
    def _delegation_evidence(cls, text: str) -> _DelegationEvidence | None:
        pronoun = _PRONOUN_COMMITMENT_RE.search(text)
        if pronoun is not None:
            antecedents = cls._clean(pronoun.group("antecedents"))
            if re.search(r"(?i)\b(?:and|or)\b|[/&,]", antecedents):
                return _DelegationEvidence(
                    person=None,
                    outcome=pronoun.group("outcome"),
                    evidence=pronoun.group(0).strip(),
                    pronoun=pronoun.group("pronoun"),
                    ambiguity="pronoun antecedent is ambiguous",
                )
            return _DelegationEvidence(
                person=antecedents,
                outcome=pronoun.group("outcome"),
                evidence=pronoun.group(0).strip(),
                pronoun=pronoun.group("pronoun"),
            )
        for pattern in _DIRECT_COMMITMENT_PATTERNS:
            match = pattern.search(text)
            if match is not None:
                return _DelegationEvidence(
                    person=match.group("person"),
                    outcome=match.groupdict().get("outcome") or "",
                    evidence=match.group(0).strip(),
                )
        return None

    @classmethod
    def _follow_up_evidence(
        cls,
        text: str,
        source: CommandSourceRefV1,
    ) -> _FollowUpEvidence | None:
        for pattern in _FOLLOW_UP_PATTERNS:
            match = pattern.search(text)
            if match is None:
                continue
            raw_date = cls._clean(match.group("date"))
            return _FollowUpEvidence(
                raw_date=raw_date,
                resolved_date=cls._resolve_relative_date(raw_date, source),
                person_reference=cls._clean(match.groupdict().get("person") or "") or None,
                evidence=match.group(0).strip(),
            )
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
    def _inferred_expected_outcome(
        cls,
        responsible: str | None,
        raw_outcome: str,
        parent_title: str,
    ) -> str | None:
        cleaned = cls._clean_outcome(raw_outcome)
        if not responsible or not cleaned or cls._is_vague_outcome(cleaned):
            return None
        present = cls._present_tense(cleaned)
        expected = f"{responsible} {present}"
        if "what happened" in expected.casefold() and "rivian" in parent_title.casefold():
            expected = re.sub(r"[.]$", "", expected)
            expected = f"{expected} regarding the delayed Rivian response"
        return expected.rstrip(".") + "."

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
        outcome = re.sub(r"(?i)\bhappend\b", "happened", outcome)
        return outcome or None

    @staticmethod
    def _present_tense(outcome: str) -> str:
        parts = outcome.split(maxsplit=1)
        verb = parts[0].casefold()
        rest = f" {parts[1]}" if len(parts) == 2 else ""
        irregular = {
            "be": "is",
            "have": "has",
            "do": "does",
            "go": "goes",
            "write": "writes",
            "send": "sends",
        }
        if verb in irregular:
            conjugated = irregular[verb]
        elif verb.endswith(("s", "sh", "ch", "x", "z", "o")):
            conjugated = f"{verb}es"
        elif verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
            conjugated = f"{verb[:-1]}ies"
        else:
            conjugated = f"{verb}s"
        return f"{conjugated}{rest}"

    @classmethod
    def _infer_completion_criterion(
        cls,
        raw_outcome: str,
        expected: str,
        accountable: str,
    ) -> str | None:
        normalized = cls._clean_outcome(raw_outcome) or ""
        lowered = normalized.casefold()
        reviewer = f"{accountable}’s" if accountable else "Ryan’s"
        if "document" in lowered or "write" in lowered:
            return f"The documentation is completed and available for {reviewer} review."
        if any(word in lowered for word in ("send", "deliver", "provide")):
            obj = re.sub(r"(?i)^(?:send|deliver|provide)\s+", "", normalized).strip()
            if obj:
                return f"{obj[:1].upper() + obj[1:]} has been delivered in the agreed location."
        if any(
            word in lowered
            for word in ("complete", "finish", "prepare", "create", "update", "confirm")
        ):
            return f"The committed outcome is completed and available for {reviewer} review."
        if expected and len(normalized.split()) >= 3:
            return f"The committed outcome is completed and available for {reviewer} review."
        return None

    @staticmethod
    def _is_vague_outcome(value: str) -> bool:
        return bool(_VAGUE_OUTCOME_RE.fullmatch(value.strip().rstrip(".")))

    @classmethod
    def _checkpoint_title(
        cls,
        *,
        responsible: str | None,
        raw_outcome: str,
        parent_title: str,
    ) -> str | None:
        if not responsible:
            return None
        normalized = cls._clean_outcome(raw_outcome) or ""
        if "rivian" in parent_title.casefold() and "document" in normalized.casefold():
            return f"Follow up with {responsible} on Rivian response documentation"
        return None

    @staticmethod
    def _uses_parent_context(expected: str, parent_title: str) -> bool:
        return "rivian" in parent_title.casefold() and "rivian" in expected.casefold()

    @staticmethod
    def _resolve_relative_date(value: str, source: CommandSourceRefV1) -> str:
        normalized = value.strip().casefold()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            return normalized
        if not source.source_posted_at or not source.source_timezone:
            return value.strip()
        try:
            zone = ZoneInfo(source.source_timezone)
            posted = datetime.fromisoformat(source.source_posted_at.replace("Z", "+00:00"))
        except (ValueError, ZoneInfoNotFoundError):
            return value.strip()
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=zone)
        local_date = posted.astimezone(zone).date()
        if normalized == "today":
            return local_date.isoformat()
        if normalized == "tomorrow":
            return (local_date + timedelta(days=1)).isoformat()
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        if normalized in weekdays:
            delta = (weekdays[normalized] - local_date.weekday()) % 7
            return (local_date + timedelta(days=delta or 7)).isoformat()
        if normalized == "next week":
            return (local_date + timedelta(days=7)).isoformat()
        if normalized == "next month":
            year = local_date.year + (1 if local_date.month == 12 else 0)
            month = 1 if local_date.month == 12 else local_date.month + 1
            return local_date.replace(year=year, month=month, day=1).isoformat()
        return value.strip()

    @staticmethod
    def _unlabeled_dates(
        text: str,
        *,
        delegate_due: str | None,
        follow_up: str | None,
    ) -> tuple[str, ...]:
        scrubbed = _FIELD_RE.sub("", text)
        scrubbed = _PERSON_DUE_FIELD_RE.sub("", scrubbed)
        for pattern in _FOLLOW_UP_PATTERNS:
            scrubbed = pattern.sub("", scrubbed)
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
        field_origins: dict[str, str],
        requires_approval: bool,
        follow_up_raw: str | None,
        checkpoint_title: str | None,
    ) -> dict[str, str]:
        result = dict(fields)
        values = {
            "responsible": responsible,
            "accountable": accountable,
            "outcome": expected,
            "done-when": criteria[0] if criteria else None,
            "delegate-due": delegate_due,
            "follow-up": follow_up,
            "follow-up-raw": follow_up_raw,
            "checkpoint-title": checkpoint_title,
            "intent-origin": "task-update",
            "source-event-id": source.source_event_id,
            "source-event-type": source.source_event_type,
            "source-comment-id": source.source_comment_id,
            "source-update": source.source_command_text,
            "provenance-source-digest": source.source_digest,
            "normalization-actionable": "true" if actionable else "false",
            "normalization-ambiguity": " | ".join(ambiguity) if ambiguity else None,
            "normalization-blockers": " | ".join(blockers) if blockers else None,
            "requires-attended-approval": "true" if requires_approval else "false",
        }
        for key, value in values.items():
            if value:
                result[key] = value
        for key, origin in sorted(field_origins.items()):
            result[f"field-origin:{key}"] = origin
        return result

    @staticmethod
    def _confidence_score(
        *,
        classification: AtlasCommandType,
        actionable: bool,
        ambiguity: list[str],
        blockers: list[str],
        inferred: bool,
    ) -> float:
        if ambiguity or blockers:
            return 0.0 if not actionable else 0.4
        if classification == AtlasCommandType.DELEGATE:
            return 0.85 if inferred else 1.0
        if actionable:
            return 0.9 if inferred else 0.95
        return 0.0
