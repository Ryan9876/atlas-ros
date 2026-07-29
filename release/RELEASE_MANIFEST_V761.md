# Atlas ROS v7.6.1 Immutable Release Manifest

Status: exact package authorized for immutable publication and controlled production activation; Ryan profile activation is not authorized.

## Exact package identity

- Release version: `7.6.1`
- Exact package source commit: `4fdda0c574b75fa5e56367aaa9355341b6b84176`
- Validated implementation merge: `1f89a58c4a988f7de92d63e9e0cf38cfb824d2e8`
- Exact retained artifact: `8742484220`
- Artifact display name: `atlas-ros-v761-user-communication-`
- Artifact SHA-256: `7cd46dda08683fe3a3a681a7398dd32820996cec48abe5eb241d0fd7a3826221`
- Source distribution SHA-256: `6945406d475901d396ee7cb4024fbb8c8420256c4f4b0f2358689fcae45b9ed2`
- Wheel SHA-256: `0c5cf0e0187b8a14badfa6c2cab8fc5f041fd31d93f3b3f5a17df240ef6eb2a9`
- SPDX SBOM SHA-256: `9b4ed28d44ccbee53c61c8c6814bebd84a754a1c9a803c50d7a840f5eaf856d1`
- Source manifest SHA-256: `f22cd5abb795b369841aefd67bab6baadbee24d692f6c4d013dc6fe57965baeb`
- Validation receipt SHA-256: `93958cc6bc1d1131723cba80f4a6c70f730e8f38ed75b03207f74f27ba286d65`
- Zero-provider-write receipt SHA-256: `2d357135116813cb9326e73e170c77ec31547c505a6dd7c68898cf19779bdc82`
- Draft immutable manifest SHA-256: `d0655d99837fe9d1c63ef28789ef3a8f855d7911696908754532a71279fb2736`
- Feature-policy file SHA-256: `ff822f9b45ab1bf5fd5092adbfb63c7f80631e5bb7868d144acbadd829ee028c`
- Feature-policy deterministic digest: `861ee645b619d46fa3183e34157835354cbaf47a118d84f15e0d0cb1fecc6b8c`
- Build count: `1`
- Full non-publishing validation run: `30498275127`
- Governing Decision: `V4D-58`
- Acceptance Review: `V4V-102`

The immutable `v7.6.1` tag must point to the publication-trigger merge commit containing this manifest, the exact authorization record, the publication controller, and the publication trigger. Package artifacts remain bound to the exact package source commit above. Publication controls must not rebuild, replace, or modify the package.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

## Release scope

Atlas ROS v7.6.1 adds governed user communication and decision adaptation contracts, deterministic projection over v7.6.0 governed evidence, a bounded policy compiler, context-specific playbooks, current-instruction and live-authority override controls, privacy and prompt-injection protections, and profile-isolation controls.

## Feature and profile state

- Software adaptation immediately after release activation: `disabled`
- Safe fallback: Atlas ROS v7.6.0 baseline with v7.5 clarification behavior
- Ryan profile included in package artifacts: `false`
- Ryan profile installed: `false`
- Ryan profile active: `false`
- Profile activation requires a separate exact governed transaction.
- Provider permission effect: `false`
- Execution authorization effect: `false`
- No additive Notion schema or production migration is required for this package-only transaction.

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative and is not part of initialization or this deployment transaction.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v7.6.0 at `a177bcebd1e97d784822e378b661a5ec17aee7d5`
- Historical rollback: Atlas ROS v7.5.2 at `28f317f89f717bbf7c8df4832cea82aee26649f2`
- Historical rollback: Atlas ROS v7.5.1 at `379892900e1c82f84a6716f46a8180d83c836aa7`
- Existing older immutable rollback records remain preserved unchanged.

## Validation and restoration evidence

The exact package passed full Ruff, strict Mypy, architecture and development-tool boundaries, 827 tests with 86.56% branch coverage, deterministic policy and privacy evidence, scoped secret scanning with zero findings, dual dependency audits with no known vulnerabilities, build-once source and wheel generation, SPDX SBOM and source-manifest generation, clean source and wheel installation, Active v7.6.0 restoration, preserved v7.5.2 restoration, nested checksum verification, package exclusion of the Ryan profile, and zero-provider-write and zero-Todoist-write validation.

The retained artifact's outer SHA-256 and all package, evidence, and nested checksum files were independently read and verified before publication authorization. The shortened artifact display name is non-authoritative; artifact ID, artifact digest, workflow run, source commit, package index, validation receipt, and nested checksums establish exact identity.

## Governing authorization

Ryan authorized the exact package and package-only activation sequence on 2026-07-29. The authorization is recorded in:

- Decision: https://app.notion.com/p/3acb8344ad2c817a90f7c81c93e5d2ce (`V4D-58`)
- Acceptance Review: https://app.notion.com/p/3acb8344ad2c81cc9e5cd0a32b877213 (`V4V-102`)
- Repository authorization record: `release/V761_EXACT_PACKAGE_AUTHORIZATION.md`

## Required activation sequence

1. Merge the exact validated implementation candidate.
2. Publish immutable tag and GitHub Release `v7.6.1` from retained artifact `8742484220` without rebuilding.
3. Independently verify tag target, release assets, checksums, package identities, clean installations, feature-policy evidence, profile exclusion, and zero-write receipts.
4. Activate canonical GitHub and Notion authority with v7.6.1 Active and v7.6.0 immediate rollback.
5. Keep the software adaptation feature disabled.
6. Keep the Ryan profile uninstalled and inactive.
7. Perform final live cross-authority, rollback, feature-policy, and integration readback.

Publication alone does not activate production authority. This package authorization does not authorize profile installation or activation.

## Preserved boundaries

No profile installation or activation, Notion schema change, autonomous scheduling, messaging, email, calendar action, credential action, integration-scope expansion, Todoist task write, record deletion, forgetting execution, or unattended live-network execution is authorized. Immutable v7.6.0 and all historical releases remain unchanged.
