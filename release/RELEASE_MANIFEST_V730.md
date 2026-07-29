# Atlas ROS v7.3.0 Immutable Release Manifest

Status: exact package authorized for immutable publication and controlled production activation.

## Exact package identity

- Release version: `7.3.0`
- Exact package source commit: `3082a8c4b4124167b5b5219a943a519fdfd63779`
- Source merge commit: `47b1799d7f3744b4e53d286cc320c4cbf292204f`
- Exact promotion-review artifact: `8709808300`
- Artifact SHA-256: `690f28b097e4b01b94388e765029eb18f49ddd7d78e724c45c107b0cd449f388`
- Source distribution SHA-256: `6e152ca6f5c1cd1644937ed9eea6582966f18bb3e558ec6c851fa2c7a6c6306e`
- Wheel SHA-256: `5be3ea8af13e70d7bf2e2fa54fc07532d8182c90ee1121e3a881c4214f7a3890`
- SPDX SBOM SHA-256: `3c7c729cbeeeeff322d5940aeed0d3ef5c501e88b1094f2947f33185e281bc99`
- Source manifest SHA-256: `58858c92825cdca7c48d91b358953392a5e8da451b4fa4555dc1aacde97b9180`
- Exact package manifest digest: `eef7451b019f5a6c8de2c8daffb089d03fdbbce5178e3657cfdb1d56a23ca195`
- Build count: `1`
- Full non-publishing validation run: `30414839587`
- Full validation result: `718` tests passed, `86.23%` coverage, secret scan passed, PyPI and OSV audits passed, exact wheel and sdist clean installs passed, deterministic replay passed, and provider writes remained `0`.

The immutable `v7.3.0` tag must point to the commit containing this manifest. The package artifacts remain bound to the exact package source commit above; the manifest commit adds release metadata only.

## Governing authorization and reviews

- Promotion decision: https://app.notion.com/p/3acb8344ad2c816e9e81ca692886a87c
- Exact package review: https://app.notion.com/p/3acb8344ad2c816d9f14df4609dc0431
- Prepublication and rollback review: https://app.notion.com/p/3acb8344ad2c81999f32f2eacad9e1e7
- Source pull request: https://github.com/Ryan9876/atlas-ros/pull/62

## Release scope

Atlas ROS v7.3.0 introduces evidence-backed Operational Awareness and explicit command-driven work lifecycle planning:

1. provider-neutral operational evidence and immutable snapshots;
2. continuous work-state intelligence;
3. delegation and commitment intelligence;
4. exception-based operating briefs;
5. execution context and resumption memory;
6. work-graph hygiene with attended repair proposals; and
7. exact, idempotent `@atlas` command lifecycle interpretation and planning.

Planning cannot authorize, adapters cannot plan or authorize, and reconciliation cannot create successor execution intent.

## Production integrations

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional, non-authoritative historical access and is not required for initialization or promotion.

## Notion production migration

The only authorized production schema change is the additive migration `atlas.v730.delegated-work.additive-commitment-fields` against Delegated Work data source `collection://6d035d30-6c3b-4e69-b67d-2f0315831eb3`.

Authorized additive fields:

- `Acceptance Status` — select: Unconfirmed, Accepted, Declined, Superseded, Not Required
- `Last Verified` — date
- `Commitment Source` — rich text
- `Expected Evidence` — rich text
- `Completion Evidence State` — select: Not Received, Partial, Received, Verified, Rejected

The migration contains no destructive operation, data rewrite, record deletion, or property removal. Rollback is to leave the additive fields unused; no destructive reversal is authorized.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v7.1.1 at `7e18113b58fcd486b5c7e8eb9368c7c70bc83bcd`
- Historical rollback: Atlas ROS v7.1.0 at `0711b045f34f5ab7b03f7a61bc80653e0d815463`
- Historical rollback: Atlas ROS v7.0.1 at `f26f5154ea6cd4b431c5a2638c439d7de9282761`
- Historical rollback: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`

Active v7.1.1 and rollback v7.1.0 assets were checksum-verified and clean-installed during the exact package validation run.

## Activation sequence

1. validate and merge this exact manifest;
2. rehearse the publication controller against artifact `8709808300`;
3. publish immutable tag and GitHub Release `v7.3.0`;
4. independently verify tag target, release assets, nested checksums, source and wheel identities, and clean installation;
5. apply the exact additive Notion migration and verify schema readback;
6. update canonical GitHub authority and generated Release Index with v7.3.0 Active and v7.1.1 immediate rollback;
7. update Notion System State to the matching production state; and
8. perform final live authority and integration readback.

Publication alone does not activate production authority.

## Preserved boundaries

No autonomous scheduling, messaging, email, calendar action, deletion, credential action, integration-scope expansion, Google Drive retirement, or unattended live-network execution is authorized. Todoist remains attended and limited to approved Ryan-owned destinations. Outlook Email and Outlook Calendar remain prohibited. Google Calendar remains contract-only and inactive.
