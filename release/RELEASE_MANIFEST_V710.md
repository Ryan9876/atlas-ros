# Atlas ROS v7.1.0 Immutable Release Manifest

Status: Prepared immutable release package. Production activation is determined exclusively by the canonical GitHub `governance/AUTHORITY.json` record and matching Notion System State after exact-package authorization, immutable publication, independent publication readback, and transactional authority activation.

- Package version: `7.1.0`
- Authority model version: `7.0`
- Minimum compatible initializer version: `7.0.1`
- Immediate immutable rollback after promotion: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback retained: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

Atlas ROS v7.1.0 consolidates the remaining v7 capabilities while preserving the existing authority model and attended-execution boundaries:

1. deterministic Google Drive dependency inventory and retirement-readiness controls without retiring or deleting Drive;
2. governed item-level historical-cleanup planning, exact authorization, readback, partial-failure handling, and receipts;
3. a version-neutral deterministic release compiler that emits candidate artifacts only;
4. production-runtime isolation from legacy, migration, provider, and release-tooling paths; and
5. verified lazy loading plus an optional authenticated, TTL-bound, read-only warm-runtime foundation.

## Startup authority

Initialization remains GitHub-first and must read these authorities in order:

1. `governance/AUTHORITY.json` from the canonical GitHub authority ref;
2. the generated `governance/RELEASE_INDEX.md` from that same ref;
3. this immutable manifest from the exact Active-release commit and verify its declared canonical digest;
4. the Notion System State URL named by `AUTHORITY.json`; and
5. the Integration Inventory named by this manifest.

Required production integrations are exactly GitHub, Notion, and Todoist. Google Drive is optional, non-authoritative historical access and is not read during initialization.

## Preserved boundaries

- Candidate compilation does not authorize, publish, or activate a release.
- Publication does not activate authority.
- Authority activation follows independent publication readback.
- No Google Drive deletion, retirement, credential revocation, or historical deletion is authorized by this release.
- No Todoist destination, label, assignment, or authorization-scope expansion is introduced.
- No autonomous scheduling, messaging, email, calendar action, deletion, credential action, or live-network execution is enabled.
- Adapters cannot plan or authorize. Planning cannot authorize. Reconciliation cannot create execution intent.
- Provider writes require an immutable authorized plan, exact operation identities, idempotency, readback, and receipts.

## Required validation

Before promotion, the exact v7.1.0 source and wheel must pass:

- Ruff, architecture validation, legacy-isolation validation, strict MyPy, complete pytest with branch coverage, and execution-planning evaluation;
- deterministic dependency policy, secret scanning, PyPI audit, and OSV audit;
- Drive-independence and disconnected-Drive initialization tests;
- deterministic release-compiler fixtures and production-manifest validation;
- staged `AUTHORITY.json`, generated Release Index, immutable-manifest digest, System State projection, and Integration Inventory agreement tests;
- build-once source and wheel construction, clean installation, and runtime identity verification;
- source manifest, SPDX SBOM, nested checksums, and startup-performance comparison;
- immutable v7.0.1, v6.5.0, and v6.2.0 restoration; and
- non-publishing final-package controller validation.

## Published workspace validity

The readable published workspace is valid only when the canonical GitHub authority record, generated GitHub Release Index, this exact immutable manifest, the exact immutable tag and GitHub Release assets, Notion System State, and the manifest-resolved Integration Inventory are readable and internally consistent. Secrets and private signing material are excluded.