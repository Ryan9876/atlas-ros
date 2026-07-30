# Atlas ROS v7.8.0 Draft Immutable Release Manifest

Status: draft candidate metadata only. This file is mutable implementation-branch documentation and does not publish, activate, or authorize a release.

## Intended package identity

- Version: `7.8.0`
- Exact source commit: pending candidate freeze
- Workflow run: pending full candidate validation
- Retained artifact ID: pending
- Artifact archive SHA-256: pending
- Source distribution SHA-256: pending
- Wheel SHA-256: pending
- SPDX SBOM SHA-256: pending
- Source manifest SHA-256: pending
- Validation receipt SHA-256: pending
- Build count: must equal `1`

## Authorized scope

- Root CLI help and lightweight status semantics
- Failed validation output replay
- SQLite database/WAL/SHM permission hardening
- Governed retry delays and sanitized Retry-After guidance
- Reconciliation uncertain-write idempotency clarity

## Preserved boundaries

Adapters remain single-attempt. Orchestration owns attended retries and journaled delay selection. Readback precedes retry after uncertain writes. Lightweight status does not claim unverified production authority. No async adapter conversion, provider-layer automatic retry, production schema migration, merge, tag, publication, authority activation, credential change, deletion, messaging, calendar action, or scheduling is included.

## Restoration baseline

The candidate workflow must resolve the live Active release and immediate rollback from `governance/AUTHORITY.json` at validation time and independently verify restoration. No release identity in this draft supersedes live authority.
