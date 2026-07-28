# ADR-013 — Drive Retirement Readiness and Governed Historical Cleanup

## Status

Accepted for the Atlas ROS v7.1.0 candidate. This decision does not authorize any provider retirement, deletion, credential revocation, or historical disposition.

## Context

Google Drive is no longer startup, runtime, release, or rollback authority. Optional historical access remains, but retirement requires proof that current operation and required evidence are independent of Drive. Historical cleanup also requires item-level retention, exclusion, authorization, readback, and receipt controls rather than folder-level assumptions.

## Decision

1. Maintain a deterministic repository and operating-record inventory of every Drive reference and classify it as runtime, startup authority, release authority, restoration, historical reference, migration tooling, documentation, or obsolete.
2. Fail retirement preflight when any current dependency remains.
3. Keep provider-specific historical access outside production runtime.
4. Represent every historical item with exact identity, digest, location, release family, retention classification, dependencies, and disposition.
5. Unknown, conflicted, active-release-dependent, or rollback-dependent items fail closed.
6. Cleanup planning remains provider-free. Execution requires an immutable plan, exact attended authorization, object and byte budgets, idempotency, bounded failure handling, readback, reconciliation, and a complete receipt.
7. The shipped implementation contains only provider-neutral contracts, planning, an in-memory validation fixture, and non-destructive Drive retirement simulation. No live delete adapter is enabled.

## Consequences

Drive can become technically retirement-ready without being retired. Historical cleanup can be validated end to end without granting destructive authority. A later transaction must identify the exact account, connector, credentials, inventory digest, exclusions, targets, budgets, and authorized operations.
