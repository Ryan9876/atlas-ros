# Atlas ROS v7.7.0 Initialization Circuit Breaker Operator Runbook

## Purpose

Operate and diagnose the bounded Quick Initialization path without broadening its authority or call budget.

## Expected clean cold trace

1. `github.authority.read`
2. `github.release_index.read`
3. `github.immutable_manifest.read`
4. `notion.system_state.read`
5. `notion.integration_inventory.read`
6. `todoist.connector_liveness.read`
7. Terminal state and receipt rendering with no external call

Expected external read count: 6. Expected provider writes: 0. Expected Google Drive reads: 0. Expected post-terminal executed calls: 0.

## Expected clean warm trace

1. Live GitHub authority read.
2. Authenticated local cache lookup and local Release Index/manifest validation.
3. Live Notion System State read.
4. Live Notion Integration Inventory read.
5. Todoist liveness read.
6. Terminal state and receipt rendering.

Expected external read count: 4. A cache rejection may fall back once to the cold immutable reads and should report `warm_fallback_to_cold`.

## Terminal outcomes

### `READY`

All authority and integration checks passed with no warning. Do not run diagnostics or extra reads inside the completed operation.

### `READY_WITH_WARNINGS`

Initialization succeeded with a real non-blocking condition, such as an authenticated cache rejection or store failure. The terminal lock is still active. Evaluate the warning outside the operation.

### `INITIALIZATION_BLOCKED`

A required read, schema, identity, digest, authority agreement, workspace, inventory, or connector-liveness check failed. Do not substitute web search, repository search, Notion search, Google Drive, memory, or another connector.

## Receipt review

Confirm:

- schema version `2.0`;
- one operation ID;
- correct Active and rollback identities;
- authority agreement and digest results;
- expected path and actual trace;
- external-read count matches the path, plus at most one eligible retry;
- rejected calls show `provider_invoked=false`;
- budget result is true;
- terminal lock is activated;
- provider writes, Google Drive reads, and post-terminal executed calls are zero.

## Failure handling

1. Preserve the receipt and exact trace.
2. Classify the failure as transient transport, access, malformed content, integrity, authority disagreement, inventory, liveness, target, state, budget, or terminal-call rejection.
3. Do not retry contradictions, digest failures, access denial, malformed authority, invalid schemas, stale authority, or terminal-state calls.
4. A transport failure is retried automatically once only when no authoritative content was returned.
5. Start Full Validation as a separate operation only when the governed escalation conditions are met.

## Recovery

- No production state is changed by Quick Initialization.
- If the candidate itself is faulty before activation, continue using Active v7.6.1.
- If v7.7.0 is later activated and rollback is required, restore the exact v7.6.1 immutable package and authority using the release-controlled rollback procedure.
- Do not change authority, publish, move tags, or write Notion System State from this runbook without exact authorization.
