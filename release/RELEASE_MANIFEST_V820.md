# Atlas ROS v8.2.0 Immutable Release Manifest

Status: exact package authorized for immutable no-rebuild publication, independent verification, and controlled production activation.

## Exact package identity

- Release version: `8.2.0`
- Exact package source commit: `887ac2e58e69bcba9ad4bac8ef4345819f88a70a`
- Validated implementation merge: `b465a98ce0e19e5c2e9f176dfa869c07b376c4ef`
- Full non-publishing validation run: `30604505487`
- Exact retained candidate artifact: `8783124836`
- Candidate artifact SHA-256: `03ea656ece8e548907ced312c99166376cc7f0c482a9c5ec21cd8b08b2411a72`
- Source distribution SHA-256: `f38c4b71f9d64be8bb76f61f9519209ee02fb0038827bef7f10ec4c03b345bfe`
- Wheel SHA-256: `a227516a3918d666f29abeb7e1ccc4d0c6a4db5f4564305477aaad8bad6aca45`
- SPDX SBOM SHA-256: `13e78efabe79e2ca0dc9f6a3243e18bc004adc0942119890ecf455ee5bf0aa40`
- Validation receipt SHA-256: `a3f730672bfad61ae7aead57ce08db31787e3d9827589e3c666fa2ec152fdfa6`
- Natural-comment evidence SHA-256: `fd32950b6c72e3a209423b4d2b05c04bd19e8d6efd2c8c28c0696742cf3843ee`
- No-migration receipt SHA-256: `2173ea523da83c1e4f233ce6527a09aa026e72123445fe32bdb23a965558b53f`
- Live reconciliation-state schema readback SHA-256: `360b31c0b7fe6ce67a86433f924dc048b9b294be16da8a7e5d8c0d3c820590c6`
- Package index SHA-256: `8b2deed9355bd268ca396852ceb03acae91de9ce93c9ac52a759a53969949121`
- Source-tree SHA-256: `be0f6f2609476cabec185ae6fcc74b5b5600139be7a7be5fb5877debd76dc42a`
- Package checksum index SHA-256: `5be3da86c84d874644d524ac723d6edbbe48d0b5b995d468e5dfd322ec99cb60`
- Evidence checksum index SHA-256: `890600bc52fb7501fc97c72bb7d99ae04bf381af67c383e2f76e7c0c2aaca49f`
- Build count: `1`
- Test result: `1,064 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.42914979757084%`
- Governing Decision: `V4D-63`
- Acceptance Review: `V4V-118`
- Authorization record SHA-256: `012c69017261fe1db5fe0b8804bf3462e8fe9dd788ab0ac1f1bbf01a7d182993`

The immutable `v8.2.0` tag must point to the publication transaction commit containing this manifest, the exact authorization record, publication controller, independent readback controller, and publication trigger. Package assets remain bound to the exact package source commit above. Publication controls must not rebuild, replace, or modify the package.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

## Release scope

Atlas ROS v8.2.0 adds deterministic natural-language Todoist comment reconciliation across governed Todoist sources and Universal Inbox ingress. It ingests parent-task and subtask comments independently of task update timestamps, preserves stable comment-event identity and provenance, recognizes bounded delegation commitments and Ryan follow-ups, resolves only safe same-comment pronouns, separates delegate delivery from Ryan checkpoint dates, proposes exact-plan-bound records, enforces one active checkpoint, performs provider readback, and guarantees replay-safe reconciliation without silently discarding unseen comments.

The feature remains attended and review-first. Natural-language interpretation cannot create execution intent, authorize provider writes, or bypass exact plan/event authorization.

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative and is not part of this promotion transaction.

## Schema and migration assessment

No production Notion schema migration is required.

- Data sources created: `0`
- Properties added, renamed, or removed: `0`
- Existing records rewritten: `0`
- Destructive operations: `0`

Complete event evidence is serialized into the existing reconciliation ledger `Notes` field as a typed JSON envelope. Local SQLite retains additive typed fields. Any future production schema expansion requires a separate release-controlled transaction.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v8.1.0 at `a46619c4b806a63ea1426f06171b53ee219d9d77`
- Historical rollback: Atlas ROS v8.0.0 at `6f05b24fd410ab1f00578019e5336185181ee265`
- Historical rollback: Atlas ROS v7.8.0 at `72974d1d7da9f07a4c8a41b73b22c0fae3770268`
- Existing older immutable rollback records remain preserved unchanged.

## Validation and restoration evidence

The exact package passed Ruff, strict MyPy, architecture and development-tool boundaries, 1,064 tests, 86.4291% total coverage, schema equivalence, deterministic replay, comment lifecycle, exact authorization, one-active-checkpoint, connector acceptance, scoped secret scanning with zero findings, PyPI and OSV audits with no known vulnerabilities, build-once source and wheel generation, clean source and wheel installation, Active v8.1.0 restoration, immediate rollback v8.0.0 restoration, and zero-provider-write, zero-Notion-write, zero-Todoist-write validation.

Independent candidate artifact replay verified every package and evidence checksum, including the live reconciliation-state schema readback, without rebuilding the package.

## Governing authorization

Ryan authorized the exact package and complete controlled promotion sequence on July 31, 2026. The authorization is recorded in:

- Decision: https://app.notion.com/p/3aeb8344ad2c8185a946d6a4e431d7b3 (`V4D-63`)
- Acceptance Review: https://app.notion.com/p/3aeb8344ad2c81a78902c0ef892391c8 (`V4V-118`)
- Repository authorization record: `release/V820_EXACT_PACKAGE_AUTHORIZATION.md`

## Required activation sequence

1. Publish immutable tag and GitHub Release `v8.2.0` from the retained artifacts without rebuilding.
2. Independently verify tag target, Release assets, checksums, package identities, clean installations, v8.1.0 restoration, and v8.0.0 historical continuity.
3. Confirm no production Notion schema migration is required.
4. Activate canonical GitHub authority with v8.2.0 Active and v8.1.0 immediate rollback.
5. Activate matching Notion System State only after GitHub activation readback.
6. Preserve v8.0.0 and older releases as historical rollback records.
7. Perform final live cross-authority, integration, rollback, integrity, preserved-boundary, and integration readback.

Publication alone does not activate production authority.

## Preserved boundaries

No production reconciliation apply, autonomous scheduling, unattended provider write, messaging, email, calendar action, credential action, integration-scope expansion, Todoist task write, record deletion, profile activation, governed intent-memory inference activation, or live-network execution is authorized. Immutable v8.1.0, v8.0.0, v7.8.0, and historical releases remain unchanged.
