# Atlas ROS v7.1.1 Active Release Manifest

Status: Mutable current projection of the Active production release. The immutable authority is `release/RELEASE_MANIFEST_V711.md` at exact commit `7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd`. Production status is determined by canonical `governance/AUTHORITY.json`, the generated Release Index, the exact immutable manifest, and matching Notion System State.

- Package version: `7.1.1`
- Authorized immutable source commit and tag target: `7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd`
- Immutable tag and GitHub Release: `v7.1.1`
- Source merge: `5c2bb3cb230c7609a07924767e2ae26b453f0492`
- Publication-controller merge: `8c2e65ce0bba62c534300d4542b5be2059a38d49`
- Canonical GitHub authority activation merge: `9197a60cdb109a3c9882a90360622972029e3237`
- Exact final artifact ID: `8704221961`
- Exact final artifact digest: `ba784bc15e01bcf19936d3ee5bf21c1fef3b71de0e7588b3660d5b6da4f36f33`
- Final source SHA-256: `250113a5053e90c8be701bd638f2dac276b25b3115a377fd5c5a78bc40f52cf7`
- Final wheel SHA-256: `10caa8768675cff65d1cd2765e1c15374e6e3b78b59ef921e9d4d78f6d236d71`
- Immutable manifest canonical digest: `508a460cc373360ce722dde2788894a338f32b3b6869d172c1144e3a229179cc`
- Canonical authority SHA-256: `0e4c9c5232845e6c5b07500f02d51f7b8a4208a8ed95d1167574d9081c486b64`
- Authority integrity digest: `6bd3cbb9eeedfaa69bb456376fb78c764267f080d4e93414cd2b3613f231e133`
- Generated Release Index digest: `34f02428a4e21c3fe4c5d950c4686ed7d204edd257ff5a1ff3288aca25be9335`
- Independent publication readback run: `30401143819`
- Independent readback evidence artifact: `8704772131`
- Independent readback evidence digest: `86dc2299354aec99d10ca8fefb94722f6195c86669aa471f786798885ea9a0e3`
- Authority validation run: `30401593774`
- Authority validation evidence artifact: `8704937434`
- Authority validation evidence digest: `36e96ba7805fc41d2dfb3ddba419146871bc6469e73816c26948522cbf5aed88`
- Promotion decision: `V4D-50`
- Governed reviews: `V4V-74`, `V4V-75`, `V4V-76`, and `V4V-77`; final live readback is recorded separately in Review Records
- Immediate immutable rollback: Atlas ROS v7.1.0 at `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Historical rollback retained: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback retained: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Provider writes outside the authorized immutable GitHub publication, exact authority-record transaction, matching Notion System State update, and current-guidance synchronization: `0`

## Startup authority

Atlas ROS initialization is GitHub-first and must read authorities in this order:

1. live `governance/AUTHORITY.json` from the canonical GitHub authority ref;
2. the generated `governance/RELEASE_INDEX.md` from that same ref or an eligible authenticated, TTL-bound, digest-bound immutable snapshot;
3. `release/RELEASE_MANIFEST_V711.md` from exact immutable commit `7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd` and verify canonical digest `508a460cc373360ce722dde2788894a338f32b3b6869d172c1144e3a229179cc`;
4. the live Notion System State URL named by `AUTHORITY.json`; and
5. the direct Integration Inventory data source named by the immutable manifest.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Required production integrations are exactly GitHub, Notion, and Todoist. Each required integration must be connected, approved, accepted, production-current, and least-privilege verified. One additional Todoist liveness read is required; GitHub and Notion liveness are satisfied by their required authority reads.

Google Drive is not read during initialization and is not a required production integration. Existing Drive content is optional, non-authoritative legacy or historical material. No Drive deletion, retirement, credential revocation, or historical cleanup is authorized by this release.

## Release scope

Atlas ROS v7.1.1 corrects Quick Initialization performance while preserving the v7 authority model and attended-execution boundaries:

1. one typed `quick_initialize` operation and compact non-authoritative receipt;
2. mandatory live canonical authority reads with authenticated, TTL-bound, digest-bound reuse only for immutable Release Index and manifest material;
3. live compact System State and direct Integration Inventory reads;
4. one additional Todoist liveness probe;
5. stage-level timings, cache-path reporting, warnings, and exact fail-closed blockers; and
6. deterministic cold/warm equivalence, cache rejection, and fallback behavior.

No Todoist destination, label, assignment, or authorization-scope expansion is introduced. No autonomous scheduling, messaging, email, calendar action, deletion, credential action, or live-network execution is enabled. Adapters cannot plan or authorize; planning cannot authorize; reconciliation cannot create execution intent.

## Validation

The exact v7.1.1 package passed focused initialization and schema tests, Ruff, architecture and legacy-isolation validation, strict MyPy, complete pytest with branch coverage, deterministic release compilation, dependency policy, secret scanning across 1,914 files with zero findings, PyPI and OSV audits with zero vulnerabilities, build-once source and wheel construction, clean installation reporting `7.1.1`, runtime verification, source manifest, SPDX SBOM, nested checksums, initialization performance evidence, startup comparison, staged-authority validation, immutable publication readback, independent authority validation, and final GitHub-first live authority readback.

Immutable v7.1.0, v7.0.1, v6.5.0, and v6.2.0 restoration completed successfully during exact-package validation and publication readback.

The readable published workspace is valid only while `AUTHORITY.json`, the generated GitHub Release Index, the exact immutable v7.1.1 manifest, the `v7.1.1` tag and Release assets, Notion System State, and the manifest-resolved Integration Inventory remain readable and internally consistent. Secrets and private signing material are excluded.
