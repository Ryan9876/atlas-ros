"""Fail-closed identity binding for natural task-update delegation.

This module enriches the existing typed command lifecycle. It does not authorize
execution, invoke providers, or create an alternative delegation workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.operational_awareness import (
    AtlasCommandType,
    AtlasCommandV1,
    OperationalSnapshotV1,
    ProviderOperationSpecV1,
    TaskUpdateLifecycleNormalizationV1,
    TodoistLifecyclePlanV1,
)


@dataclass(frozen=True, slots=True)
class ResolvedPersonIdentity:
    """One exact snapshot-backed person identity."""

    display_name: str
    canonical_identity: str
    notion_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class PersonIdentityResolution:
    """Deterministic exact-match result for one person reference."""

    query: str
    matches: tuple[ResolvedPersonIdentity, ...]

    @property
    def resolved(self) -> ResolvedPersonIdentity | None:
        return self.matches[0] if len(self.matches) == 1 else None


@dataclass(frozen=True, slots=True)
class TaskUpdatePersonIdentityResolver:
    """Resolve names only from authoritative identities present in the snapshot.

    Each normalized record may expose ``extra.person_directory`` as a list of
    mappings with ``display_name``, ``canonical_identity``, optional ``aliases``,
    and optional ``notion_user_id``. Exact case-insensitive matching is used.
    """

    def resolve(
        self,
        snapshot: OperationalSnapshotV1,
        query: str,
    ) -> PersonIdentityResolution:
        normalized_query = query.strip().casefold()
        matches: dict[str, ResolvedPersonIdentity] = {}
        for record in snapshot.normalized_records:
            raw_directory = record.extra.get("person_directory", ())
            if raw_directory is None:
                continue
            if not isinstance(raw_directory, list | tuple):
                raise ValueError("person_directory must be a list or tuple")
            for raw_entry in raw_directory:
                if not isinstance(raw_entry, dict):
                    raise ValueError("person_directory entries must be mappings")
                identity = self._parse_entry(raw_entry)
                aliases = raw_entry.get("aliases", ())
                if aliases is None:
                    aliases = ()
                if not isinstance(aliases, list | tuple) or not all(
                    isinstance(item, str) for item in aliases
                ):
                    raise ValueError("person_directory aliases must be strings")
                names = (identity.display_name, *aliases)
                if normalized_query in {item.strip().casefold() for item in names}:
                    existing = matches.get(identity.canonical_identity)
                    if existing is not None and existing != identity:
                        raise ValueError("conflicting person identity directory entries")
                    matches[identity.canonical_identity] = identity
        return PersonIdentityResolution(
            query=query,
            matches=tuple(sorted(matches.values(), key=lambda item: item.canonical_identity)),
        )

    @staticmethod
    def _parse_entry(raw_entry: dict[str, Any]) -> ResolvedPersonIdentity:
        display_name = str(raw_entry.get("display_name") or "").strip()
        canonical_identity = str(raw_entry.get("canonical_identity") or "").strip()
        notion_user_id_value = raw_entry.get("notion_user_id")
        notion_user_id = (
            str(notion_user_id_value).strip() if notion_user_id_value is not None else None
        )
        if not display_name or not canonical_identity:
            raise ValueError(
                "person_directory entries require display_name and canonical_identity"
            )
        return ResolvedPersonIdentity(
            display_name=display_name,
            canonical_identity=canonical_identity,
            notion_user_id=notion_user_id or None,
        )


def bind_natural_delegation_identities(
    normalization: TaskUpdateLifecycleNormalizationV1,
    snapshot: OperationalSnapshotV1,
) -> TaskUpdateLifecycleNormalizationV1:
    """Bind exact identities to a natural delegation proposal or fail closed."""

    if normalization.classification != AtlasCommandType.DELEGATE:
        return normalization

    resolver = TaskUpdatePersonIdentityResolver()
    fields = dict(normalization.proposed_command.fields)
    ambiguity = list(normalization.ambiguity)
    blockers = list(normalization.blockers)
    evidence = list(normalization.evidence)

    responsible_resolution = (
        resolver.resolve(snapshot, normalization.responsible_party)
        if normalization.responsible_party
        else None
    )
    responsible = responsible_resolution.resolved if responsible_resolution else None
    if normalization.responsible_party and responsible is None:
        ambiguity.append(
            "responsible party identity is unresolved"
            if responsible_resolution and not responsible_resolution.matches
            else "responsible party identity is ambiguous"
        )
        blockers.append("Responsible party identity must resolve uniquely")
    elif responsible is not None:
        fields["responsible"] = responsible.display_name
        fields["responsible-identity"] = responsible.canonical_identity
        if responsible.notion_user_id:
            fields["responsible-notion-user-id"] = responsible.notion_user_id
        evidence.append(
            f"responsible identity resolved: {responsible.canonical_identity}"
        )

    accountable_resolution = (
        resolver.resolve(snapshot, normalization.accountable_party)
        if normalization.accountable_party
        else None
    )
    accountable = accountable_resolution.resolved if accountable_resolution else None
    if normalization.accountable_party and accountable is None:
        ambiguity.append(
            "accountable party identity is unresolved"
            if accountable_resolution and not accountable_resolution.matches
            else "accountable party identity is ambiguous"
        )
        blockers.append("Accountable party identity must resolve uniquely")
    elif accountable is not None:
        fields["accountable"] = accountable.display_name
        fields["accountable-identity"] = accountable.canonical_identity
        if accountable.notion_user_id:
            fields["accountable-notion-user-id"] = accountable.notion_user_id
        evidence.append(
            f"accountable identity resolved: {accountable.canonical_identity}"
        )

    fields["normalization-ambiguity"] = " | ".join(dict.fromkeys(ambiguity))
    fields["normalization-blockers"] = " | ".join(dict.fromkeys(blockers))
    fields["identity-resolution-source"] = "snapshot.person_directory"
    fields = {key: value for key, value in fields.items() if value}

    command = AtlasCommandV1.create(
        command_type=normalization.proposed_command.command_type,
        source=normalization.proposed_command.source,
        subject=(
            responsible.display_name
            if responsible is not None
            else normalization.proposed_command.subject
        ),
        fields=fields,
    )
    unique_ambiguity = tuple(dict.fromkeys(ambiguity))
    unique_blockers = tuple(dict.fromkeys(blockers))
    return TaskUpdateLifecycleNormalizationV1.create(
        source=normalization.source,
        classification=normalization.classification,
        proposed_command=command,
        actionable_transition=normalization.actionable_transition,
        responsible_party=(
            responsible.display_name
            if responsible is not None
            else normalization.responsible_party
        ),
        accountable_party=(
            accountable.display_name
            if accountable is not None
            else normalization.accountable_party
        ),
        expected_outcome=normalization.expected_outcome,
        completion_criteria=normalization.completion_criteria,
        delegate_due=normalization.delegate_due,
        follow_up_checkpoint=normalization.follow_up_checkpoint,
        confidence=ConfidenceAssessment(
            score=(min(normalization.confidence.score, 1.0) if not unique_blockers else 0.4),
            rationale=(
                "natural delegation fields and person identities resolved deterministically"
                if not unique_blockers
                else "natural delegation failed closed on unresolved material identity"
            ),
        ),
        provenance=normalization.provenance,
        evidence=tuple(dict.fromkeys(evidence)),
        ambiguity=unique_ambiguity,
        blockers=unique_blockers,
        field_origins=dict(normalization.field_origins),
        requires_attended_approval=normalization.requires_attended_approval,
        resolved_follow_up_date=normalization.resolved_follow_up_date,
    )


def bind_natural_delegation_plan(
    plan: TodoistLifecyclePlanV1,
) -> TodoistLifecyclePlanV1:
    """Attach resolved identity and deferred Notion-URL bindings to the base plan."""

    command = plan.command_interpretation.command
    if (
        command.command_type != AtlasCommandType.DELEGATE
        or command.fields.get("intent-origin") != "task-update"
    ):
        return plan

    responsible_identity = command.fields.get("responsible-identity")
    accountable_identity = command.fields.get("accountable-identity")
    if not responsible_identity or not accountable_identity:
        raise ValueError("natural delegation plan requires resolved person identities")

    notion = plan.notion_operations[0]
    notion_payload = dict(notion.payload)
    notion_payload.update(
        {
            "intent_origin": "task-update",
            "responsible_identity": responsible_identity,
            "accountable_identity": accountable_identity,
            "responsible_notion_user_id": command.fields.get(
                "responsible-notion-user-id"
            ),
            "accountable_notion_user_id": command.fields.get(
                "accountable-notion-user-id"
            ),
        }
    )
    notion_expected = dict(notion.expected_readback)
    notion_expected.update(
        {
            "responsible_identity": responsible_identity,
            "accountable_identity": accountable_identity,
        }
    )
    bound_notion = ProviderOperationSpecV1.create(
        provider=notion.provider,
        action=notion.action,
        target=notion.target,
        payload=notion_payload,
        idempotency_key=notion.idempotency_key,
        expected_readback=notion_expected,
    )

    bound_todoist: list[ProviderOperationSpecV1] = []
    for operation in plan.todoist_operations:
        if operation.action != "upsert_current_checkpoint":
            bound_todoist.append(operation)
            continue
        payload = dict(operation.payload)
        payload.pop("authoritative_record_url", None)
        payload["authoritative_record_url_binding"] = {
            "provider": "notion",
            "operation_idempotency_key": bound_notion.idempotency_key,
            "record_identity": bound_notion.target,
            "readback_field": "canonical_url",
        }
        payload["description_template"] = (
            "Authoritative Delegated Work: {authoritative_record_url}; "
            f"parent outcome: {plan.next_action_projection.parent_outcome.canonical_record_id}"
        )
        bound_todoist.append(
            ProviderOperationSpecV1.create(
                provider=operation.provider,
                action=operation.action,
                target=operation.target,
                payload=payload,
                idempotency_key=operation.idempotency_key,
                expected_readback=operation.expected_readback,
            )
        )

    return TodoistLifecyclePlanV1.create(
        command_interpretation=plan.command_interpretation,
        parent_outcome=plan.parent_outcome,
        notion_operations=(bound_notion,),
        todoist_operations=tuple(bound_todoist),
        next_action_projection=plan.next_action_projection,
        maximum_object_count=plan.maximum_object_count,
        authorization_scope=plan.authorization_scope,
        expected_readback=tuple(
            f"{operation.provider}:{operation.target}:{operation.operation_digest}"
            for operation in (bound_notion, *bound_todoist)
        ),
        compensation_behavior=plan.compensation_behavior,
        blockers=plan.blockers,
    )
