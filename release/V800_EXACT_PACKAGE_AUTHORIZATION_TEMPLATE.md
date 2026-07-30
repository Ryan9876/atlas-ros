# Atlas ROS v8.0.0 Exact-Package Authorization Record — Pending Decision

Status: exact validation evidence is bound below, but this record does not authorize merge, publication, migration, or activation. Governing Decision, Acceptance Review, and Ryan's exact-package authorization remain **PENDING**.

## Exact validated package

- Exact package source commit: `674f0c979dec8f83a1610c7435e633e2d33e673a`
- Full validation run: `30574165764`
- Candidate artifact ID: `8772036696`
- Candidate artifact SHA-256: `9202086b86df6f727daa097d476a82099ebdbd97e8e85aa433160cb8f40464ea`
- Evidence run: `30574165698`
- Evidence artifact ID: `8771997275`
- Evidence artifact SHA-256: `e480e5f2ecda736fdabae36e71fba3a8628e1b9e7240085a24fc8a6eda999f95`
- Source distribution SHA-256: `2bfd6fda0879b9508809bdb28a41f43a664bee1098ce3325b3574223cd864047`
- Wheel SHA-256: `0a308d4b4d23a86b99fe66a1e17b89340ff5ab84091b9eca277f461d13f8f8a5`
- SBOM SHA-256: `65c8642671b1729bb775540d7bcdb5af05d14659d39169c940b8c13b5a14d9ec`
- Source manifest SHA-256: `667774768014e45fb821964d2c78f8225b34f74869e7e5cb7398b1d7bb79cc05`
- Source-tree SHA-256: `a4c0ee2e4222979cbca4939fb38a405168b531f0bd6527574fe60d70205e9d8d`
- Validation receipt SHA-256: `49bf52c882ca99cefe9b7a3fdf02c0578124c2771c1dde59aa729534e2d6f5dd`
- Build count: `1`

## Validation gates

- Test result: `1014 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.56235017216581%`
- Statement coverage: `90.41722745625842%`
- Branch coverage: `70.16941391941391%`
- Ruff: passed
- Strict MyPy: passed
- Architecture and development-tool boundaries: passed
- Dependency audits: PyPI and OSV passed with zero known vulnerabilities
- Secret scan: passed, 49 files scanned, zero findings
- Clean source and wheel install: passed
- Atlas ROS v7.8.0 active restoration: passed
- Atlas ROS v7.7.0 immediate rollback restoration: passed
- Provider dry run: zero writes
- Replay/idempotency: passed
- Notion/Todoist readback and partial-failure recovery fixtures: passed
- Unresolved and ambiguous person identity planning: blocked
- Cookbook and shared fixture verification: passed
- Additive migration validation: `validated_unapplied`, zero destructive operations, zero live reads, zero live writes

## Intended controlled sequence

An eventual exact authorization must cover all of the following without substitution:

1. Use only the retained source distribution and wheel identified above; do not rebuild.
2. Preserve Atlas ROS v7.8.0 as the live rollback target unless the governing Decision explicitly and validly changes the chain.
3. Merge and publish only the exact authorized release-control transaction.
4. Publish immutable tag and GitHub Release `v8.0.0`.
5. Independently verify tag target, release assets, checksums, clean installation, and v7.8.0 restoration.
6. Apply the additive Notion migration only in the attended activation transaction after publication verification.
7. Activate GitHub and Notion authority only after independent verification.
8. Perform final live authority, integration, migration, rollback, provider-write, and preserved-boundary readback.
9. Confirm zero unauthorized provider writes occurred.

## Required approvals

- Governing Decision: **PENDING**
- Acceptance Review: **PENDING**
- Ryan exact-package authorization: **PENDING**
- Publication authorization: **PENDING**
- Migration application authorization: **PENDING**
- Authority activation authorization: **PENDING**

A branch, PR, merge, test pass, retained artifact, draft manifest, or completed template is not authorization. This record becomes operative only when the pending approvals identify this exact package and the exact controlled sequence.
