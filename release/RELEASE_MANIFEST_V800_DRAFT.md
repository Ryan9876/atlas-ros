# Atlas ROS v8.0.0 Validated Candidate Release Manifest

Status: the exact package identified below passed non-publishing full validation. Publication, migration application, merge, and production activation are not authorized.

## Exact package identity

- Release: Atlas ROS v8.0.0
- Package version: `8.0.0`
- Intended tag: `v8.0.0`
- Exact package source commit: `674f0c979dec8f83a1610c7435e633e2d33e673a`
- Full non-publishing validation run: `30574165764`
- Exact retained candidate artifact: `8772036696`
- Candidate artifact SHA-256: `9202086b86df6f727daa097d476a82099ebdbd97e8e85aa433160cb8f40464ea`
- Evidence workflow run: `30574165698`
- Exact retained evidence artifact: `8771997275`
- Evidence artifact SHA-256: `e480e5f2ecda736fdabae36e71fba3a8628e1b9e7240085a24fc8a6eda999f95`
- Source distribution SHA-256: `2bfd6fda0879b9508809bdb28a41f43a664bee1098ce3325b3574223cd864047`
- Wheel SHA-256: `0a308d4b4d23a86b99fe66a1e17b89340ff5ab84091b9eca277f461d13f8f8a5`
- SPDX SBOM SHA-256: `65c8642671b1729bb775540d7bcdb5af05d14659d39169c940b8c13b5a14d9ec`
- Source manifest SHA-256: `667774768014e45fb821964d2c78f8225b34f74869e7e5cb7398b1d7bb79cc05`
- Source-tree SHA-256: `a4c0ee2e4222979cbca4939fb38a405168b531f0bd6527574fe60d70205e9d8d`
- Validation receipt SHA-256: `49bf52c882ca99cefe9b7a3fdf02c0578124c2771c1dde59aa729534e2d6f5dd`
- Package checksum index SHA-256: `48337c17c1ea56560bd87e90479ad9a8e3e079d5ad8cd51f84303252db523b08`
- Build count: `1`
- Test result: `1014 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.56235017216581%`
- Statement coverage: `90.41722745625842%`
- Branch coverage: `70.16941391941391%`
- Governing Decision: **PENDING**
- Acceptance Review: **PENDING**
- Ryan exact-package authorization: **PENDING**

The retained source distribution and wheel are the only package artifacts eligible for later exact-package authorization. No later control or publication transaction may rebuild, replace, or modify them.

## Release scope

Atlas ROS v8.0.0 adds deterministic task-update lifecycle normalization for qualified natural-language delegation while preserving the explicit `@atlas delegate` command and the existing typed command lifecycle. The normalizer classifies `delegate`, `waiting-on`, `blocked`, `complete`, `update`, or no actionable transition, then routes qualified proposals through the current `CommandLifecycleService`, canonical provider planning, attended authorization, idempotent execution, readback, and reconciliation architecture.

Natural delegation requires explicit ownership evidence, a uniquely resolved snapshot-backed responsible identity, a uniquely resolved accountable identity, an expected outcome, and explicit completion criteria. A person-name mention alone is not delegation and is not identity resolution. Delegate delivery due date and Ryan follow-up checkpoint remain separate typed fields. Ambiguity fails closed before provider planning.

## Validation result

The exact package passed Ruff, strict MyPy, architecture and development-tool boundary checks, 1,014 tests, cookbook conformance, additive migration validation, scoped secret scanning with zero findings across 49 changed files, PyPI and OSV dependency audits with zero known vulnerabilities, zero-write provider planning and replay checks, Notion/Todoist readback and failure-recovery fixtures, build-once source and wheel generation, clean source and wheel installation, live Atlas ROS v7.8.0 restoration, immediate rollback Atlas ROS v7.7.0 restoration, exact receipt generation, SPDX 2.3 SBOM generation, and source-manifest generation.

## Additive migration

`release/v800-notion-schema-migration.yaml` is validated and unapplied. It proposes ten additive Delegated Work fields, performs no destructive operation, and had zero live reads and zero live writes during validation. Production application remains unauthorized until the exact package is published, independently verified, and included in a separately authorized attended activation transaction.

## Required production integrations

Required integrations remain exactly GitHub, Notion, and Todoist. No integration-scope change is included. Google Drive remains optional and non-authoritative.

## Rollback evidence

Validation resolved live authority rather than hard-coding the rollback chain. It verified the active v7.8.0 tag target and immutable manifest digest, downloaded its published source and wheel, and matched both against the source and wheel digests in live authority. It also resolved the v7.7.0 immutable manifest from its authority-provided commit, extracted the package digests, downloaded the published package assets, and verified both digests. No rollback authority was changed.

## Preserved boundaries

No autonomous scheduling, unattended provider write, messaging, email, calendar, credential, deletion, profile activation, broad intent inference, or live-network execution is authorized. Interpretation does not authorize execution. Planning does not authorize execution. Adapters cannot create execution intent. Provider writes remain on the existing attended and governed authorization path.

## Remaining controlled sequence

1. Review the exact validated candidate and evidence artifacts.
2. Record the governing Decision and Acceptance Review.
3. Obtain Ryan's explicit authorization for this exact package and controlled sequence.
4. Merge or otherwise publish release controls only as authorized without rebuilding the package.
5. Publish immutable tag and GitHub Release `v8.0.0` from the retained artifacts.
6. Independently verify tag target, assets, checksums, package identities, clean installation, and v7.8.0 restoration.
7. Apply the additive migration only inside the authorized activation transaction.
8. Activate GitHub and Notion authority only after publication verification.
9. Perform final authority, integration, provider-write, migration, rollback, and preserved-boundary readback.

Publication alone does not activate production authority. Atlas ROS v7.8.0 remains the sole Active release until the complete controlled sequence succeeds.
