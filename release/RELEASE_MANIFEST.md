# Atlas ROS v7.1.0 Active Release Manifest

Status: Mutable current projection of the Active production release. The immutable authority is `release/RELEASE_MANIFEST_V710.md` at exact commit `0711b045f34f5ab7b03f7a61bc80653e0d815463`. Production status is determined by canonical `governance/AUTHORITY.json`, the generated Release Index, the exact immutable manifest, and matching Notion System State.

- Package version: `7.1.0`
- Authorized immutable source commit and tag target: `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Immutable tag and GitHub Release: `v7.1.0`
- Canonical GitHub authority activation merge: `55e711f94f66f8354c67b4306d487182fff28c4e`
- Publication-controller merge: `e1e71574078588afb76fd5fef9ad4a111094eafc`
- Exact final artifact ID: `8700442825`
- Exact final artifact digest: `bb1d2a735ef6c175dd5a41fda067c8d1301883eaa9d413b38fa56346ae8fa483`
- Final source SHA-256: `fb69bef625125bf477bb3dda3d1b09dfec43af0ccf6a3d78c998bf9df8139834`
- Final wheel SHA-256: `7e199f44463b6c2f646441cac4d50b47b0fe4bdb92b0837492013063cb8b976a`
- Immutable manifest canonical digest: `13d277c6244657d1f4379a19c36ba532d0ffd7aa23f339fcdbca896edbfb9733`
- Independent publication readback run: `30392150475`
- Independent readback evidence artifact: `8701367346`
- Independent readback evidence digest: `a44ca3a70f902974080274f80657c129cc5c51314956689394c0b1047769436c`
- Authority validation run: `30392656615`
- Authority validation evidence artifact: `8701562583`
- Authority validation evidence digest: `8262bdeb0da71809852ed8c8df96c82a4543c6048865ca922d050113a9ac0499`
- Promotion decision: `V4D-46`
- Governed reviews: `V4V-66`, `V4V-67`, `V4V-68`, `V4V-69`, and `V4V-70`
- Immediate immutable rollback: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback retained: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Provider writes outside the authorized immutable GitHub publication, exact authority-record transaction, and matching Notion System State update: `0`

## Startup authority

Atlas ROS initialization is GitHub-first and must read authorities in this order:

1. `governance/AUTHORITY.json` from the canonical GitHub authority ref;
2. the generated `governance/RELEASE_INDEX.md` from that same ref;
3. `release/RELEASE_MANIFEST_V710.md` from exact immutable commit `0711b045f34f5ab7b03f7a61bc80653e0d815463` and verify canonical digest `13d277c6244657d1f4379a19c36ba532d0ffd7aa23f339fcdbca896edbfb9733`;
4. the Notion System State URL named by `AUTHORITY.json`; and
5. the Integration Inventory named by the immutable manifest.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Required production integrations are exactly GitHub, Notion, and Todoist. Each required integration must be connected, approved, accepted, production-current, and least-privilege verified.

Google Drive is not read during initialization and is not a required production integration. Existing Drive content is optional, non-authoritative legacy or historical material. No Drive deletion, retirement, credential revocation, or historical cleanup is authorized by this release.

## Release scope

Atlas ROS v7.1.0 consolidates the remaining v7 capabilities while preserving the existing authority model and attended-execution boundaries:

1. deterministic Google Drive dependency inventory and retirement-readiness controls without retiring or deleting Drive;
2. governed item-level historical-cleanup planning, exact authorization, readback, partial-failure handling, and receipts;
3. a version-neutral deterministic release compiler that emits candidate artifacts only;
4. production-runtime isolation from legacy, migration, provider, and release-tooling paths; and
5. verified lazy loading plus an optional authenticated, TTL-bound, read-only warm-runtime foundation.

No Todoist destination, label, assignment, or authorization-scope expansion is introduced. No autonomous scheduling, messaging, email, calendar action, deletion, credential action, or live-network execution is enabled. Adapters cannot plan or authorize; planning cannot authorize; reconciliation cannot create execution intent.

## Validation

The exact v7.1.0 package passed Ruff, architecture and legacy-isolation validation, strict MyPy, 686 tests with zero failures, execution-planning evaluation, deterministic dependency policy, secret scanning across 1,913 files with zero findings, PyPI and OSV audits with zero vulnerabilities, build-once source and wheel construction, clean installation reporting `7.1.0`, runtime verification, source manifest, SPDX SBOM, nested checksum verification, startup comparison, staged-authority validation, immutable publication readback, and final live authority readback.

Immutable v7.0.1, v6.5.0, and v6.2.0 restoration completed successfully during exact-package validation and publication readback.

The readable published workspace is valid only while `AUTHORITY.json`, the generated GitHub Release Index, the exact immutable v7.1.0 manifest, the `v7.1.0` tag and Release assets, Notion System State, and the manifest-resolved Integration Inventory remain readable and internally consistent. Secrets and private signing material are excluded.
