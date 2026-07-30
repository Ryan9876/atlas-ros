# ADR-0080: Deterministic Task-Update Delegation Normalization

- **Status:** Proposed for Atlas ROS v8.0.0; not active production authority
- **Date:** 2026-07-30

## Context

Atlas ROS v7.8.0 supports explicit typed lifecycle commands. Normal task updates can contain the same lifecycle evidence, but treating arbitrary language as executable intent would weaken fail-closed and provider-write boundaries.

## Decision

Introduce `TaskUpdateLifecycleNormalizer` before the existing lifecycle interpreter. It uses deterministic, narrow evidence rules and produces an existing `AtlasCommandV1`. It recognizes explicit delegation/ownership, waiting-on, blocked, complete, update, or no actionable transition. Qualified delegation requires a unique responsible person, an exact governed responsible-party identity, an exact governed accountable-party identity, expected outcome, and completion criteria. Textual name recognition is not identity resolution. Identity lookup uses exact aliases supplied in the authoritative operational snapshot and fails closed on zero or multiple matches. Delegate due date and Ryan follow-up checkpoint are separate fields.

The normalizer cannot authorize execution or call providers. Its output flows through `CommandLifecycleService`, the existing canonical planner, attended authorization, adapters, idempotent transaction journal, readback, and reconciliation. The Notion operation must be read back first; only the returned Delegated Work URL may be injected into the dependent Todoist checkpoint mapping. Generic update behavior is unchanged; a no-action update does not create a follow-up.

## Consequences

- Explicit `@atlas delegate` behavior remains compatible.
- Natural delegation has zero false positives across governed negative fixtures.
- Material ambiguity, unresolved person identity, or ambiguous person identity blocks provider planning.
- Stable Delegated Work identity is based on parent, delegate, and outcome; a changed follow-up updates that record and replaces the previous checkpoint.
- The Notion schema change is additive and activation-controlled. Person properties receive governed provider IDs rather than display names, and the Todoist link is bound to the actual Notion readback URL.
- No integration, permission, scheduling, messaging, calendar, credential, deletion, or live-network scope is expanded.

## Rejected alternatives

- **Parallel natural-language workflow:** rejected because it would duplicate lifecycle, idempotency, reconciliation, and authorization controls.
- **LLM-only intent classification:** rejected because it cannot meet deterministic replay and zero-false-positive requirements.
- **Treat every update as follow-up intent:** rejected because it creates spurious Ryan tasks and changes generic update behavior.
- **Single date field:** rejected because delegate delivery and Ryan checkpoint dates have different owners and operational meanings.
