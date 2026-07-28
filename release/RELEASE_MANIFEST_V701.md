# Atlas ROS v7.0.1 Immutable Release Manifest

Status: Corrective patch package. Production activation is determined exclusively by the canonical GitHub `governance/AUTHORITY.json` record and matching Notion System State after exact-package authorization, immutable publication, and independent readback.

- Package version: `7.0.1`
- Authority model version: `7.0`
- Minimum compatible initializer version: `7.0.1`
- Immediate immutable rollback after promotion: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Corrective scope

Atlas ROS v7.0.1 corrects the v7.0.0 activation contradiction and implements the intended GitHub-only startup chain:

1. read `governance/AUTHORITY.json` from GitHub at the current authority ref;
2. verify the generated `governance/RELEASE_INDEX.md` at the same GitHub authority ref;
3. resolve and digest-verify this versioned immutable manifest at the commit named by `AUTHORITY.json`;
4. read the Notion System State URL named by `AUTHORITY.json`;
5. resolve the Integration Inventory URL from this manifest; and
6. require GitHub, Notion, and Todoist—exactly—as the production integration set.

Google Drive is not read during initialization and is not a required production integration. Existing Drive content may remain available as optional, non-authoritative legacy or historical material. This release does not authorize Drive deletion, retirement, credential revocation, or historical cleanup.

## Preserved boundaries

- No autonomous scheduling, messaging, email, calendar action, deletion, or live-network execution.
- No Todoist destination, label, assignment, or authorization-scope expansion.
- Adapters cannot plan or authorize.
- Planning cannot authorize.
- Reconciliation cannot create execution intent.
- Provider writes require an immutable authorized plan, exact operation identities, idempotency, readback, and receipts.
- Candidate validation performs zero provider writes.

## Required validation

Before promotion, the exact v7.0.1 source and wheel must pass:

- Ruff, architecture validation, strict MyPy, complete pytest with branch coverage, and execution-planning evaluation;
- deterministic dependency policy, secret scanning, PyPI audit, and OSV audit;
- authority compiler, generated Release Index, immutable-manifest digest, System State, and Integration Inventory agreement tests;
- explicit rejection of Google Drive as a required integration;
- clean installation and runtime identity verification;
- immutable v7.0.0 and v6.5.0 restoration;
- checksum, SBOM, source-manifest, and nested-evidence verification; and
- non-publishing final-controller validation.

## Published workspace validity

The readable published workspace is valid only when the canonical GitHub authority record, generated GitHub Release Index, this immutable manifest, exact GitHub tag and Release assets, Notion System State, and manifest-resolved Integration Inventory are readable and internally consistent. Google Drive is outside that startup authority chain.
