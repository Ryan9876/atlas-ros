# Atlas ROS v7.8.0 Implementation Contract

Status: implementation in progress on a draft pull request. This document is not an immutable release manifest and does not activate production authority.

## Authority baseline

- Active authority at branch creation: Atlas ROS v7.7.0.
- Immediate rollback: Atlas ROS v7.6.1.
- Required integrations: GitHub, Notion, and Todoist.
- Google Drive is optional, non-authoritative, and was not read.

## Authorized implementation scope

1. Root CLI help handling.
2. Failed validation output diagnostics.
3. SQLite database, WAL, and SHM permission hardening.
4. Governed retry delays and sanitized Retry-After guidance.
5. Lightweight runtime status semantics that do not infer live authority.
6. Reconciliation idempotency clarity without weakening uncertain-write recovery.

## Preserved boundaries

- Adapters remain single-attempt transports.
- Orchestration owns retry policy, delay selection, evidence, and uncertain-write recovery.
- Readback precedes retry after uncertain writes.
- Lightweight status does not claim an unverified Active production release.
- No asynchronous adapter conversion or production schema migration is included.
- Validation and packaging must perform zero provider writes and zero Todoist writes.
- No merge, tag, publication, release activation, credential change, deletion, messaging, calendar action, or scheduling is authorized by this implementation branch.

## Completion gate

The branch may advance only to promotion-ready candidate status. Exact-package promotion requires separate authorization after all tests, CI, package evidence, restoration checks, checksums, and zero-write receipts pass.
