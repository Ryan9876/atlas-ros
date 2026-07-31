# Atlas ROS v8.2.0 Draft Rollback and Promotion Plan

## Promotion prerequisites

1. Re-resolve live authority and verify v8.1.0 Active with v8.0.0 immediate rollback, unless live authority has legitimately changed before promotion.
2. Freeze the exact source commit.
3. Pass Ruff, strict MyPy, full tests and coverage, architecture boundaries, connector contracts, secret scan, dependency audits, clean builds, and clean installs.
4. Build once and retain source distribution, wheel, SBOM, source-tree identity, validation receipt, natural-comment evidence, and checksum indexes.
5. Demonstrate zero production Notion/Todoist/provider writes during validation.
6. Restore and verify the live Active release and immediate rollback from immutable published artifacts.
7. Independently read back the candidate artifact without rebuilding.
8. Record the governing Decision and Acceptance Review.
9. Obtain Ryan's exact-package and complete-sequence authorization.
10. Merge/publish only in the authorized order, independently verify publication, confirm zero schema migration, activate authority, and perform final live readback.

## Rollback

At promotion time, resolve rollback from live authority rather than from this draft. Under the current authority baseline, v8.0.0 is the immediate rollback. Restore its immutable package and matching GitHub/Notion authority if a post-publication or activation check fails.

No reverse Notion schema migration is required because v8.2.0 adds no production Notion properties. Event envelopes stored in existing `Notes` remain inert evidence under older releases.

## Prohibited in candidate preparation

No default-branch merge, immutable tag, GitHub Release, System State change, authority activation, production Notion write, production Todoist write, or production reconciliation apply.
