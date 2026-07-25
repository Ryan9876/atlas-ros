# Execution Orchestration Standard

## Purpose

This standard governs the attended transition from a validated `ExecutionPlanV2` to provider
operations. It ends after a verified receipt or a truthful non-success result. Reconciliation,
checkpoint mutation, new planning, follow-up scheduling, and unplanned work are outside this
boundary.

## Responsibility model

| Component | Owns | Must not own |
|---|---|---|
| Execution Planner | existence, projection, horizon, task economy | authorization, providers, transactions |
| Command Factory | exact ordered projection of an existing plan | adding, removing, or replanning work |
| Execution Orchestrator | authorization, state, sequence, retry, compensation, receipt | provider API details, task existence |
| Todoist execution adapter | target resolution, rendering, upsert, move, hierarchy/readback | planning, authorization, retry policy |
| Notion execution adapter | schema mapping, record/link operations, readback | field ownership, planning, reconciliation |
| Reconciliation service | downstream comparison and checkpoints | orchestration transaction ownership |

## Authorization

Canonical execution requires `ExecutionAuthorizationV2`. The actor must be Ryan, the authority must
be `production_promotion_owner`, and the authorization digest must verify. Plan ID, plan digest,
action, providers, operation types, maximum object count, expiry, revocation, and replay policy are
checked before `applying`. A generic Boolean is accepted only at the attended W03 boundary and is
immediately translated into this exact scope.

## Deterministic sequence

For a Todoist parent tree:

1. resolve target;
2. read existing parent;
3. upsert and verify parent;
4. read existing children;
5. upsert and verify each planned child in sequence;
6. verify complete hierarchy and ordering;
7. perform and verify explicitly commanded Notion writeback;
8. aggregate the receipt.

Zero-subtask plans create no placeholders. Adapters cannot add operations.

## State, journal, and evidence

Every transition must exist in `LEGAL_TRANSITIONS`. Each journal entry includes the prior digest and
its own deterministic digest. Sequence numbers are contiguous. Serialized state contains provider
references and sanitized errors but never credentials, headers, tokens, or unnecessary content.

## Idempotency

All keys are deterministic, secret-free, action-bound, and plan-digest-bound. Verified replay
returns the stored verified result. Partial replay reads provider state and resumes with the same
keys. A timeout after apply triggers readback before create is attempted again.

## Retry policy

Only transport, timeout, rate-limit, and provider 5xx failures are retryable. Maximum attempts are
bounded and recorded. Authorization, validation, schema, permission, readback, destructive, and
unknown failures stop. No unattended schedule is created.

## Partial failure and compensation

A partial transaction lists applied and unapplied operations. Safe compensation requires explicit
command scope. Destructive compensation is prohibited unless authorized. When safe state cannot be
proven, the final state is `manual_recovery_required` with provider, operation, evidence reference,
and a concrete Ryan-owned instruction. Partial, compensated, failed, and manual-recovery results
never set `applied=true`.

## Provider contracts

Todoist descriptions must contain exact headings `**Objective:**` and `**Done when:**` with
non-empty task-specific content. Parent moves preserve child count, parent references, descriptions,
and order. Notion operations require a caller-supplied mapping contract and fail closed on schema
drift, unknown writable fields, duplicate identities, or readback mismatch.

## Simulation

Simulation validates the same plan, authorization, ordering, idempotency, retry, and recovery
structure using supplied fake ports. It performs no provider write and returns a `simulated`
transaction with `applied=false`. Simulation is never authorization.

## Release gates

The exact candidate must pass strict typing, lint, architecture enforcement, full regression,
coverage, the 60+ case orchestration benchmark, security audits, dependency policy, build,
clean-wheel installation, schema loading, checksums, SBOM consistency, draft publication readback,
fake-provider recovery, no-live-write proof, and Drive-independent restoration.
