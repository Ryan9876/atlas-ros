# v8.3.0 Event Reconciliation Contract

## Event sources

| Provider | Supported signals | Current-state requirement |
|---|---|---|
| Todoist | `item:added`, `item:updated`, `item:completed`, `item:uncompleted`, `item:deleted`, `note:added`, `note:updated`, `note:deleted` | Fetch active/completed task and relevant comments before planning |
| Notion | `page.created`, `page.content_updated`, `page.properties_updated`, `data_source.content_updated` | Fetch the current page/data source; confirm authoritative Universal Inbox membership |
| Backstop | Bounded incremental provider change enumeration | Uses the same envelope, queue, planner, and deduplication path |
| Manual | Attended replay, re-plan, and repair | Uses original causation/checkpoint evidence and the same pipeline |

## Canonical envelope

Version `8.3` records provider/event type, delivery and canonical identities, relevant object identities, provider and receipt timestamps, initiator, execution surface, raw-body digest, normalized-snapshot digest, correlation/causation, causal depth, checkpoint/sync token, policy version, object version, and origin marker. Sensitive payloads are not required for durable evidence.

The durable state machine is:

`Received -> Validated -> Snapshot Loaded -> Planned -> Policy Evaluated -> Applying -> Readback Verified -> Applied`

Terminal/waiting states are `Duplicate`, `No Change`, `Informational`, `Ignored`, `Awaiting Approval`, `Blocked`, `Failed`, and `Dead Letter`.

## Deduplication and ordering

- Exact provider delivery IDs are unique per provider.
- Semantic duplicates compare provider, canonical identity, object version, and normalized snapshot digest; every delivery is still retained as evidence.
- Workers claim with expiring leases. Production runtime selection must add durable per-canonical-object coordination across nodes.
- Event timestamps and cursors are evidence, never identity.
- A stale event is ignored only after current-state retrieval proves it is incorporated.
- Replay produces the same plan digest and zero duplicate mutations through stable idempotency keys.

## Transaction contract

An immutable event plan binds events, snapshot digests, authority/policy versions, canonical mapping, ordered typed mutations, expected values, idempotency keys, checkpoint, conflicts, expiry, and expected readback. Immediately before applying, the worker reloads the provider snapshot. Changed state invalidates the plan and requires re-planning.

Cross-provider atomicity is never claimed. Each successful operation and readback is receipted. Any failed or indeterminate transaction preserves the old checkpoint and enters recovery.

## Universal Inbox

Automatic task creation is eligible only for an approved Ryan-created capture with explicit `#Work` or `#Personal` destination, explicit outcome/task, Ryan responsibility, explicit valid due date/priority if present, no delegation/external recipient/shared workspace/prohibited action, no duplicate, one parent, and no more than five subtasks. Otherwise it is informational, duplicate, awaiting approval, or blocked; speculative placeholder tasks are prohibited.
