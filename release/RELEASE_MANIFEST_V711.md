# Atlas ROS v7.1.1 Immutable Release Manifest Candidate

Status: Prepared authority-neutral corrective-release candidate. Production activation remains determined exclusively by a future exact GitHub authority transaction and matching Notion System State update after exact-package authorization, immutable publication, and independent publication readback.

- Package version: `7.1.1`
- Authority model version: `7.0`
- Minimum compatible initializer version: `7.0.1`
- Immediate immutable rollback after promotion: Atlas ROS v7.1.0 at `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Historical rollback retained: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback retained: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: collection://46af021f-eb9a-4eba-b10c-4523e70df0c3

## Corrective release scope

1. consolidate Quick Initialization behind one typed read-only operation and compact receipt;
2. always read live `governance/AUTHORITY.json` while allowing authenticated, TTL-bound, digest-bound reuse of the immutable generated Release Index and immutable active-release manifest;
3. retain live reads for mutable System State and Integration Inventory state;
4. use a direct governed Integration Inventory data-source reference and compact projection contracts;
5. satisfy GitHub and Notion liveness through their required authority reads and perform only one additional Todoist read probe;
6. provide stage-level monotonic timing, cache path, warnings, and exact blocked conditions without returning full authority documents; and
7. validate through a minimal, single-job corrective workflow that avoids live connector calls and duplicate builds.

## Startup authority

Initialization remains GitHub-first and logically ordered:

1. live canonical `governance/AUTHORITY.json`;
2. the generated Release Index identified by authority, from live GitHub or an eligible digest-bound immutable snapshot;
3. the immutable active-release manifest from its exact immutable commit, from live GitHub or an eligible digest-bound immutable snapshot;
4. compact live Notion System State projection; and
5. direct live Integration Inventory query using the manifest-declared data source.

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Google Drive remains optional, non-authoritative historical access and is not read during initialization.

## Preserved boundaries

- The warm cache is disposable and non-authoritative.
- `AUTHORITY.json`, mutable System State, current integration readiness, authorization, execution intent, credentials, and provider truth are never served from the warm cache.
- Any cache mismatch, expiration, authentication failure, corruption, or unsupported schema falls back to the canonical cold path or fails closed.
- No production Notion projection write or integration-scope change is authorized by this candidate.
- No autonomous scheduling, messaging, email, calendar action, deletion, credential action, or live-network execution is enabled.
- Provider writes remain zero during initialization.
- Publication and authority activation remain separate exact transactions.

## Required validation

Before promotion, the exact v7.1.1 source and wheel must pass focused quality checks, architecture and legacy isolation, strict MyPy, complete pytest with branch coverage, deterministic cold/warm equivalence, cache rejection and fallback tests, compact projection and receipt schema validation, build-once clean installation, dependency/security validation, initialization performance evidence, source manifest and SPDX SBOM generation, nested checksums, immutable v7.1.0 restoration, and non-publishing final-package controller validation.

## Published workspace validity

The readable published workspace remains valid only when canonical GitHub authority, generated Release Index, exact immutable manifest, exact immutable tag and Release assets, Notion System State, and manifest-resolved Integration Inventory are readable and internally consistent. Secrets and private signing material are excluded.
