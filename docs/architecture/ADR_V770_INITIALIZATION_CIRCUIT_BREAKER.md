# ADR — Atlas ROS v7.7.0 Deterministic Initialization Circuit Breaker

## Status

Candidate implementation decision. Production activation requires separate exact-package authorization.

## Context

The v7.1.1 Quick Initialization path already reads the minimum authoritative records in a compact sequence. Its ordering and call count were primarily consequences of orchestration structure, however, rather than a single operation-scoped pre-provider enforcement boundary. A future adapter, retry, diagnostic, or response-rendering change could therefore introduce an additional external read after a terminal result.

## Decision

Introduce `InitializationOperation` as the sole operation-scoped authorization object for Quick Initialization. It owns:

- the explicit state machine;
- exact capability-to-target bindings;
- external-read and retry budgets;
- deterministic trace and rejection evidence;
- irreversible terminal state;
- pre-provider authorization for every initialization-scoped external call.

The orchestration transitions the operation before each allowed call and passes the exact capability and target to `execute_external`. The provider callable is invoked only after state, capability, target, duplication, and budget checks pass.

## State machine

```text
NOT_STARTED
  -> READING_AUTHORITY
  -> READING_RELEASE_INDEX
  -> READING_IMMUTABLE_MANIFEST
  -> READING_SYSTEM_STATE
  -> READING_INTEGRATION_INVENTORY
  -> CHECKING_CONNECTOR_LIVENESS
  -> READY | READY_WITH_WARNINGS | INITIALIZATION_BLOCKED
```

Every non-terminal active state may fail closed to `INITIALIZATION_BLOCKED`. Terminal states have no outgoing transition.

The warm path traverses the same Release Index and immutable-manifest validation states but records authenticated local validation instead of external provider reads. It then resumes the common live-state path.

## Pre-provider decision order

For every attempted external call:

1. Reject when the operation is terminal.
2. Match the capability required by the current state.
3. Match the exact target bound from live authority or the immutable manifest.
4. Reject a capability already completed in the operation.
5. Enforce the external-read and retry budget.
6. Record the attempt by connector and target.
7. Invoke the provider.
8. Record completion or failure.
9. Retry only when the typed failure is transient and the one retry remains.

## Terminal lock

`terminalize` sets an irreversible terminal state before receipt construction. A later call raises `InitializationAlreadyTerminal`, records a rejection with `provider_invoked=false`, and does not execute the provider callable. The error includes terminal status, operation ID, attempted capability, target, reason, and deterministic sequence.

## Error handling

- Invalid transitions block the operation.
- Capability, target, duplicate, and budget violations block before provider invocation.
- Provider failures are recorded as invoked failures.
- Integrity and semantic validation happen locally after the raw read and do not trigger provider retries.
- If Quick Initialization fails before terminal state, the operation terminalizes as `INITIALIZATION_BLOCKED` and emits one receipt.

## Warm-cache decision

The cache remains authenticated and non-authoritative. It is accepted only when the live authority-derived source digest, schema version, repository, immutable commit, manifest path, Release Index digest, and manifest digest all match. Cached documents undergo the same local validation as cold reads. A rejection permits one deterministic cold fallback, not search or alternative targets.

## Full Validation separation

`quick_initialize` does not call `initialize_full`. Full Validation remains an independently invoked operation. This prevents a successful bounded operation from silently broadening its capabilities or budget.

## Consequences

### Benefits

- Call count and ordering become enforceable invariants.
- Terminal state prevents external work introduced by downstream orchestration, adapters, retries, diagnostics, telemetry, rendering, or natural-language override attempts.
- Rejection evidence proves whether a provider was invoked.
- The receipt becomes suitable for deterministic release and live-readback evidence.

### Costs

- New initialization capabilities and targets require explicit state-machine and matrix changes.
- Provider adapters must route through the operation context.
- Receipt schema and tests require additive maintenance.

## Rejected alternatives

- Prompt-only restrictions: not a runtime enforcement boundary.
- Connector-specific wrappers only: do not protect cross-connector orchestration or post-terminal behavior.
- Timing thresholds: cannot prove call count or pre-provider denial.
- General-purpose policy engine during initialization: would expand dependencies and could load prohibited profile, memory, or playbook surfaces.
