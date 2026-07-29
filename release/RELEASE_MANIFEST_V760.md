# Atlas ROS v7.6.0 Immutable Release Manifest

Status: exact package authorized for immutable publication and controlled production activation.

## Exact package identity

- Release version: `7.6.0`
- Exact package source commit: `9454f229bc489890b308b083050260dd69995899`
- Validated implementation merge: `758748bbc7d981ac45e6cf38622110693e89db18`
- Exact retained artifact: `8739787363`
- Artifact name: `atlas-ros-v760-governed-intent-memory-9454f229bc489890b308b083050260dd69995899`
- Artifact SHA-256: `1b70f6d73b7aabea37247369544f7790d09949feaa1dad3a7932a3af4469c382`
- Source distribution SHA-256: `45bbb603278a54d8385f5ac244a556e0d15aa1f1d6ce7716a3ee34aa85049db7`
- Wheel SHA-256: `0aa3adc3f5cab33de15778e92211258fe6910ea9ca75191de5483e0d3c46a0b9`
- SPDX SBOM SHA-256: `63f832a34a4cfe37b03205358769530740231eac86d1539844e49eaf2d6d1cd8`
- Source manifest SHA-256: `0b11225c44c27ae623af1b8fc80a51c08116001cb75124e0d44e4cb8ab360ef1`
- Validation receipt SHA-256: `2760f23872efe3068dfbc1c1c61e58d7e02000c58fecd2fb5b37ffd93ec84139`
- Draft immutable manifest SHA-256: `044df67cd69a5dee361b70bafe6ccae0ace08e204abe343387d155b1f7fb335b`
- Build count: `1`
- Full non-publishing validation run: `30491239732`
- Governing Decision: `V4D-57`
- Acceptance Review: `V4V-99`

The immutable `v7.6.0` tag must point to the publication-trigger merge commit containing this manifest, the exact authorization record, and the authorized publication controller. Package artifacts remain bound to the exact package source commit above. Publication metadata and governed controls must not rebuild, replace, or modify the package.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

## Release scope

Atlas ROS v7.6.0 adds governed, inspectable, correctable, context-isolated intent memory while preserving current-instruction and live-authority precedence. The release:

1. adds typed contracts for governed intent evidence, contextual scope, freshness, eligibility, deterministic indexing, inspection, correction, contradiction, retirement, user-control receipts, and governed forgetting tombstones;
2. preserves accepted v7.5.1 and v7.5.2 source references and digests without rewriting predecessor evidence;
3. fails closed across user, domain, project, responsibility, request type, and sensitivity context boundaries;
4. makes current explicit instructions and live authority override memory immediately;
5. ships intent-memory inference disabled;
6. permits inspection, correction, and retirement only after the exact schema and migration are applied and read back;
7. keeps forgetting execution disabled unless an evidence-specific exact authorization, provider mutation, and live readback are completed; and
8. changes no Todoist destination, integration scope, credential, messaging, calendar, scheduling, deletion, or live-network boundary.

## Exact production schema transaction

Create exactly three additive Notion data sources under the existing Production Databases parent `https://app.notion.com/p/3a3b8344ad2c819293ebd1e9b776ecd9`, modifying no existing data source:

1. `Governed Intent Evidence`
2. `Active Intent Memory Index`
3. `Intent User Control Receipts`

- Schema-plan SHA-256: `7059751eea962e7d8b83c4cfe2491206a500891943a6353de73b763a2eb869ed`
- Schema-plan deterministic digest: `7d8f3c0a70aee998751a19e304ffc5559916c05935b03fe0726bea04f7c431d1`
- Expected pre-migration record count: `0` in each new data source
- Existing Universal Inbox, Review Records, Decision Log, Integration Inventory, and all other production data sources remain unchanged.

## Exact migration transaction

Authorized sources:

- Universal Inbox: `collection://7bc7d289-299f-4160-95c9-921ee15ce505`
- Review Records: `collection://0881c279-46d0-4673-9477-616008bfe477`
- v7.5.2 evaluation corpus: `tests/fixtures/v752_clarification_cases.json`

Authorized destinations:

- `governed-intent-evidence`
- `active-intent-memory-index`
- `intent-user-control-receipts`

Authorized deterministic results:

- Input snapshot digest: `a1a6567da9371aad00ba8f5ed430cd6acbade0b35c4d5e53b6e4613a924d5335`
- Proposed output digest: `896836a00823a2321add076ca3682c43b0846b1c4dd3dfe66009e82f4f411810`
- Proposal and replay digest: `39b78504af528ad91948e9ea25f2c608b3d54ae8f54a2608b515675165fb9f2a`
- Create count: `0`
- Update count: `0`
- Skip count: `13`
- Duplicate count: `0`

The twelve evaluation fixtures and Review `V4V-90` remain excluded because they are synthetic, speculative, or unconfirmed rather than confirmed production intent evidence.

## Feature-policy transaction

- Feature-policy SHA-256: `5ec9f7ecd7e871c2992437d0106f42fcfcd5af6226666daf46ab0eb2db3adab4`
- Feature-policy deterministic digest: `dc2578c08a2d5eb15a333dda434a445a8802b788a721ca8f1185c3e3a9386ad9`
- Immediately after v7.6.0 authority activation: `disabled`
- After exact schema and migration readback: `inspection`
- Correction after readback: enabled
- Retirement after readback: enabled
- Intent inference: disabled pending separate exact authorization
- Forgetting execution: disabled
- Safe fallback: Atlas ROS v7.5.2 clarification behavior

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative and is not part of initialization or this deployment transaction.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v7.5.2 at `28f317f89f717bbf7c8df4832cea82aee26649f2`
- Historical rollback: Atlas ROS v7.5.1 at `379892900e1c82f84a6716f46a8180d83c836aa7`
- Historical rollback: Atlas ROS v7.5.0 at `f2a14c1e401debe77040d0db836e343be6f337e3`
- Historical rollback: Atlas ROS v7.4.5 at `88ccec11df6695b91fc2cc703105c42cd21e9f01`
- Existing older immutable rollback records remain preserved unchanged.

## Validation and restoration evidence

The exact package passed full Ruff, strict Mypy, architecture and development-tool boundaries, 797 tests with 86.69% coverage, deterministic schema and migration replay, context-isolation and user-control regressions, scoped secret scanning, dual dependency audits, privacy review, build-once source and wheel generation, SPDX SBOM and source-manifest generation, clean source and wheel installation, Active v7.5.2 restoration, v7.5.1 rollback restoration, nested checksum verification, and zero-provider-write and zero-Todoist-write validation.

The retained artifact's outer SHA-256 and all package, evidence, and nested checksum files were independently read and verified before publication authorization.

## Governing authorization

Ryan authorized the exact package, schema, migration, rollback, and feature-policy sequence on 2026-07-29. The authorization is recorded in:

- Decision: https://app.notion.com/p/3acb8344ad2c8145a07febedb3174e3a (`V4D-57`)
- Acceptance Review: https://app.notion.com/p/3acb8344ad2c8125a4daf459b0d66097 (`V4V-99`)
- Repository authorization record: `release/V760_EXACT_PACKAGE_AUTHORIZATION.md`

## Required activation sequence

1. Merge the exact validated implementation candidate.
2. Publish immutable tag and GitHub Release `v7.6.0` from retained artifact `8739787363` without rebuilding.
3. Independently verify the tag target, release assets, checksums, package identities, clean installations, schema and migration evidence, feature-policy evidence, and zero-write receipts.
4. Activate canonical GitHub and Notion authority with v7.6.0 Active, v7.5.2 immediate rollback, and intent-memory inference disabled.
5. Create and read back the exact three additive Notion data sources.
6. Apply and read back the exact migration, producing zero destination records and the authorized counts.
7. Enable inspection, correction, and retirement only after successful schema and migration readback.
8. Keep inference and forgetting execution disabled.
9. Perform final live cross-authority, schema, migration, feature-policy, rollback, and integration readback.

Publication alone does not activate production authority. Authority activation alone does not authorize schema, migration, or feature-policy changes outside the exact sequence above.

## Preserved boundaries

No autonomous scheduling, messaging, email, calendar action, credential action, integration-scope expansion, Todoist task write, record deletion, forgetting execution, or unattended live-network execution is authorized. Immutable v7.5.2 and all historical releases remain unchanged.
