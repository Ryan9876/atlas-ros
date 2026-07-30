# Atlas ROS v7.8.0 Immutable Release Manifest

Status: exact package authorized for immutable publication and controlled production activation.

## Exact package identity

- Release version: `7.8.0`
- Exact package source commit: `b9ce0f2674ec685e7e2f3e2dd86810db84db3e70`
- Validated implementation merge: `d0955c261884668c7e862fc1aa9e65eac410a702`
- Full non-publishing validation run: `30515580159`
- Exact retained candidate artifact: `8748751862`
- Candidate artifact SHA-256: `839b8b9e4455553dcedcece4527839f05da21e8394d2212e9cbca8c293d71d70`
- Evidence workflow run: `30515580168`
- Exact retained evidence artifact: `8748722912`
- Evidence artifact SHA-256: `d92ece88e779450c28c3e0db7a824b3e689fab25bd63f7c86116996795da518f`
- Source distribution SHA-256: `c9644b9196fd8d5c43b3fa6211ed1901924401b2f3419711a248dcd8f14105ad`
- Wheel SHA-256: `c7c8daf6926160334c3947ca7a86496cad9b86c2894abdc4dbe4a56a6cf6125a`
- SPDX SBOM SHA-256: `6e35a81f31ec78d4cbffd58b3e65c675d9c41eafe62fc375cefe8500a389bb88`
- Source manifest SHA-256: `6e6d0ad22ae9828f5bba17b18c23d2572b043b408479d13f91418cdfa7934ba7`
- Source-tree SHA-256: `56502e35b843fd9a5f6e5371b74166707af690cde572ca74912fc7c8165eeae0`
- Validation receipt SHA-256: `663d2ea3aac7d3b9715c869f2a4e88abd6116f95943b391378f46a71fe97a861`
- Build count: `1`
- Test result: `972 passed`
- Branch coverage: `86.59%`
- Governing Decision: `V4D-60`
- Acceptance Review: `V4V-108`

The immutable `v7.8.0` tag must point to the publication transaction commit containing this manifest, the exact authorization record, publication controller, independent readback controller, and publication trigger. Package artifacts remain bound to the exact package source commit above. Publication controls must not rebuild, replace, or modify the package.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

## Release scope

Atlas ROS v7.8.0 delivers corrective runtime hardening across six authorized areas: canonical root CLI help and fail-closed lightweight status semantics; exact replay of failed validation output with stream separation; SQLite database, WAL, and SHM permission hardening; governed retry delays with bounded `Retry-After` support; removal of unverified Active-release claims from lightweight status; and reconciliation uncertain-write idempotency clarification.

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative and is not part of initialization or this deployment transaction.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v7.7.0 at `71d849b77a53b8f0ba5a9379ff45b44869756819`
- Historical rollback: Atlas ROS v7.6.1 at `91532b8f6b38ea82ef232d1181ef78418471b66b`
- Existing older immutable rollback records remain preserved unchanged.

## Validation and restoration evidence

The exact package passed Ruff, strict MyPy, architecture and development-tool boundaries, 972 tests with 86.59% branch coverage, scoped secret scanning, dual dependency audits, build-once source and wheel generation, clean source and wheel installation, Active v7.7.0 restoration, immediate rollback v7.6.1 restoration, SPDX 2.3 SBOM generation, exact source-manifest generation, and zero-provider-write and zero-Todoist-write validation.

## Governing authorization

Ryan authorized the exact package and controlled activation sequence on 2026-07-30. The authorization is recorded in:

- Decision: https://app.notion.com/p/3adb8344ad2c81ed9a48c612ea89ce53 (`V4D-60`)
- Acceptance Review: https://app.notion.com/p/3adb8344ad2c813db793c3d5ddf1e1f9 (`V4V-108`)
- Repository authorization record: `release/V780_EXACT_PACKAGE_AUTHORIZATION.md`

## Required activation sequence

1. Publish immutable tag and GitHub Release `v7.8.0` from the retained artifacts without rebuilding.
2. Independently verify tag target, Release assets, checksums, package identities, clean installations, and rollback restoration.
3. Activate canonical GitHub and Notion authority with v7.8.0 Active and v7.7.0 immediate rollback.
4. Preserve v7.6.1 and older releases as historical rollback records.
5. Perform final live cross-authority, rollback, integrity, and integration readback.

Publication alone does not activate production authority.

## Preserved boundaries

No Notion schema change, autonomous scheduling, messaging, email, calendar action, credential action, integration-scope expansion, Todoist task write, provider write, record deletion, profile activation, intent-memory operation, or unattended live-network execution is authorized. Immutable v7.7.0, v7.6.1, and all historical releases remain unchanged.
