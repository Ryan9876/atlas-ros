# Atlas ROS v8.3.0 Immutable Software Release Manifest

Status: exact package authorized for immutable no-rebuild publication,
independent verification, and controlled release-authority activation. Production
event-runtime and bounded-auto-apply activation remain held.

## Exact package identity

- Release version: `8.3.0`
- Exact package source commit: `ac546f10ee4c1e140d17beaae32f7ea77eb12a51`
- Validated implementation merge: `3e0bf74bf92ab49b6325ab9754a9b258eb23243f`
- Full validation run: `30655903724`
- Retained candidate artifact: `8803236640`
- Candidate artifact SHA-256: `93c4486dd588890b17fcbce2f8703df5dcb60268a1195a5a5bdb472304679d15`
- Source distribution SHA-256: `d180ac3367229b6bdf5ca160acb5221e8800807909bef85b30aa3615347fafbf`
- Wheel SHA-256: `d76a43aa99e629fe8055920f325028a2b64eefa6f10e1d0497419805b622f5fe`
- SPDX SBOM SHA-256: `77d3d0bbc6b118703aba007cf3068b9d1c83eedefcae1a58ecaeba28fed4f28d`
- Validation receipt SHA-256: `85c2748c154c48df9a57d68bd2690eafa8dc3e941c4588b2227382dc55d9f0e8`
- Package index SHA-256: `6fa7abe238f9e9cf7a26b697a8718b77e1a6b7cfa5e95d13c3cae0f6701c7162`
- Source-tree SHA-256: `104c468cdcb73c14672bb5558046f38ede12c385d5ad22513c8541666fbbd936`
- Package checksum index SHA-256: `f082d42eee941740052281beee987470f0524d3cb0b324eed20105ae65aef9f1`
- Evidence checksum index SHA-256: `759e305065c815618b241de2995dca449cf58d532897310d5273e9ec85573eb1`
- Build count: `1`
- Test result: `1,114 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.35697198857936%`
- Governing Decision: `V4D-65`
- Acceptance Review: `V4V-122`
- Automation Register: `V4M-6`

The immutable `v8.3.0` tag must point to the publication transaction commit
containing this manifest, the exact authorization, no-rebuild publication
controller, independent readback workflow, and checksum-bound publication
trigger. Package assets remain bound to the exact package source commit above and
must not be rebuilt.

Integration Inventory authority remains the v8.2.1-owned inventory until release
authority activation: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b,
data source `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`.

## Release scope

v8.3.0 adds an event-control layer around existing ROS planning and reconciliation:
authenticated Todoist and Notion webhook contracts, durable event state,
delivery and semantic deduplication, aggregate leases, retry/dead-letter recovery,
bounded provider backstops, feedback-loop verification, exact approval binding,
Universal Inbox eligibility limits, deterministic policy evaluation, operator
controls, and migration/restoration evidence.

The release preserves the v8.2.1 production `Execution Reconciliation State`
ledger and verified checkpoint. Both historical W04 identities remain prohibited,
unrestored, and unwritten.

## Runtime and policy state at software activation

- Runtime mode: `MONITOR_ONLY`
- Kill switch: enabled
- Ingress: disabled
- Planning worker: disabled
- Automatic application: disabled
- Approval executor: disabled
- Backstop: disabled
- Replay: disabled
- Production webhooks: not registered or activated by this release
- Production provider writes during validation: `0`
- Automation Register `V4M-6`: `validated_not_active`, autonomy `A0 Observe`

Policy `8.3.0-rc1` is published as an inactive contract. It does not become
production write authority until an approved runtime, secret model, provider
subscriptions, retention/backup ownership, monitor-only parity evidence, and a
separate exact bounded-auto-apply activation decision are completed and read back.

## Validation and restoration

The exact package passed scoped Ruff, strict MyPy, architecture and development
boundary checks, 1,114 tests, 86.35697198857936% coverage, zero-finding scoped
secret scanning, PyPI and OSV dependency audits, build-once source and wheel
generation, clean source and wheel installation, Active v8.2.1 restoration, and
immediate rollback v8.2.0 restoration. Validation performed zero production
provider writes and did not restore or write W04.

## Rollback chain after release-authority activation

- Immediate rollback: Atlas ROS v8.2.1 at
  `38285a988ef0e265ad859474c3bdcb58a1744649`
- Historical rollback: Atlas ROS v8.2.0 at
  `64c38eb4e83f6edf2d6cff28f7c7556a2c84c0c9`
- Existing older immutable rollback records remain preserved unchanged.

## Governing authorization

- Decision: https://app.notion.com/p/3aeb8344ad2c81c8b815fde947109483
  (`V4D-65`)
- Acceptance Review:
  https://app.notion.com/p/3aeb8344ad2c81cab689d6efc3c8f6c5 (`V4V-122`)
- Automation Register:
  https://app.notion.com/p/3aeb8344ad2c81a9b9bdc2c2bcab045f (`V4M-6`)
- Repository authorization: `release/V830_EXACT_PACKAGE_AUTHORIZATION.md`

## Required release sequence

1. Publish immutable tag and GitHub Release `v8.3.0` from retained artifact
   `8803236640` without rebuilding.
2. Independently verify the tag, every release asset, checksums, clean installs,
   v8.2.1 restoration, v8.2.0 continuity, W04 boundary, and inactive runtime
   controls.
3. Activate canonical GitHub release authority with v8.3.0 Active and v8.2.1
   immediate rollback.
4. Activate matching Notion System State only after GitHub activation readback.
5. Perform final cross-authority, integration, rollback, integrity, ledger,
   automation-state, and runtime-disabled readback.

Publication alone does not activate release authority, webhooks, the event
runtime, or autonomous provider writes.

## Preserved boundaries

No production webhook deployment, credential creation or change, integration-scope
expansion, bounded-auto-apply activation, messaging, email, calendar action,
live-network execution, record deletion, W04 access, or unrelated provider write
is authorized by this manifest.
