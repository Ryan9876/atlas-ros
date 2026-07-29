# Atlas ROS v7.4.0 Immutable Release Manifest

Status: exact package authorized for immutable publication and controlled production activation.

## Exact package identity

- Release version: `7.4.0`
- Exact package source commit: `d3641e2c967ed4a592736171dce5b88e51c9117a`
- Source merge commit: `8290b2a9cc1e66925b069eda5e4eabb237946a43`
- Exact promotion-review artifact: `8711718012`
- Artifact SHA-256: `270f9e4443536ce83c5bc4e0bf6af867db7cae087f24f1eff272d80ccd872d4b`
- Source distribution SHA-256: `12d555568ad451d4f8316290b5b0a6d8b83289feba04aa7fccaa293d4d772ae7`
- Wheel SHA-256: `22fe5269a24454a42824838e49c1ec1d0c86521954c4e6947d98917e9450c882`
- SPDX SBOM SHA-256: `178d1cf7828c9a9888c4abc4fe0c0c11267153595b20cb33dcbecfe241fff88c`
- Source manifest SHA-256: `8dbad420d6745404e70cbf35a8d9a94629e067808ff63b37a62ae4c2ae004658`
- Evidence package SHA-256: `f6bf9b6de0d31086981c36f5bc80f933d7da746d0fe4a58fd3f34cda5371ce74`
- Build count: `1`
- Full non-publishing validation run: `30420431986`
- Full validation result: complete tests passed with `86.00%` branch-aware coverage; Ruff, strict MyPy, architecture validation, secret scan, PyPI and OSV audits, exact wheel and source clean installs, Active and rollback restoration, manual fallback, and non-publishing controller validation passed; provider writes remained `0`.

The immutable `v7.4.0` tag must point to the commit containing this manifest. The package artifacts remain bound to the exact package source commit above; the manifest commit adds release metadata only.

## Governing authorization and reviews

- Promotion decision: https://app.notion.com/p/3acb8344ad2c810baec7c6eb6bbaff6d
- Exact package review: https://app.notion.com/p/3acb8344ad2c81b99363cbd55f2cc8e9
- Prepublication and rollback review: https://app.notion.com/p/3acb8344ad2c817ab62bc305c640af9d
- Source pull request: https://github.com/Ryan9876/atlas-ros/pull/68

## Release scope

Atlas ROS v7.4.0 introduces the Feature Delivery Acceleration Foundation:

1. versioned feature implementation, Definition of Done, and change-impact contracts;
2. canonical edit, feature, branch, and candidate validation orchestration;
3. deterministic machine-readable development receipts;
4. conservative change-impact analysis operating in shadow mode only;
5. development-tooling isolation from production runtime;
6. declarative fixture and workflow registries;
7. lean draft CI with complete final candidate validation;
8. build-once exact artifact reuse; and
9. documented manual fallback and recovery.

Impact analysis cannot suppress established or candidate validation gates. Development tooling does not create execution authority, provider intent, or production runtime dependencies.

## Production integrations

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional, non-authoritative historical access and is not required for initialization or promotion.

## Production schema state

Atlas ROS v7.4.0 requires no production Notion schema migration. Existing production data-source schemas remain unchanged. No destructive operation, data rewrite, property removal, record deletion, or rollback reversal is authorized.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v7.3.0 at `51fdeefda8330c8e11bd74336d5f6a569a78e789`
- Historical rollback: Atlas ROS v7.1.1 at `7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd`
- Historical rollback: Atlas ROS v7.1.0 at `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Historical rollback: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`

Active v7.3.0 and immediate rollback v7.1.1 assets were checksum-verified and clean-installed during the exact package validation run.

## Activation sequence

1. validate and merge this exact manifest;
2. rehearse the publication controller against artifact `8711718012`;
3. publish immutable tag and GitHub Release `v7.4.0`;
4. independently verify tag target, release assets, nested checksums, source and wheel identities, and clean installation;
5. update canonical GitHub authority and generated Release Index with v7.4.0 Active and v7.3.0 immediate rollback;
6. update Notion System State to the matching production state; and
7. perform final live authority and integration readback.

Publication alone does not activate production authority.

## Preserved boundaries

No autonomous scheduling, messaging, email, calendar action, deletion, credential action, integration-scope expansion, Google Drive retirement, Todoist write, or unattended live-network execution is authorized. Todoist remains attended and limited to approved Ryan-owned destinations. Outlook Email and Outlook Calendar remain prohibited. Google Calendar remains contract-only and inactive.
