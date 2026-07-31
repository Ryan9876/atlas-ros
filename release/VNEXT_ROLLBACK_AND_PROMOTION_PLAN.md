# Draft Rollback and Promotion Plan

## Promotion prerequisites

1. Re-resolve live authority and the current immediate rollback.
2. Complete Ruff, strict MyPy, full tests, architecture checks, secret scan, dependency audits, clean source/wheel builds, and clean installs.
3. Build once and bind exact package, source tree, SBOM, migration, and evidence checksums.
4. Validate provider dry run with zero Notion and Todoist writes.
5. Record a governing Decision and Acceptance Review.
6. Obtain Ryan's exact-package authorization.
7. Publish without rebuilding and independently read back the immutable release.
8. Apply only the authorized additive ledger migration and read it back.
9. Activate GitHub and Notion authority only after publication and migration verification.
10. Perform final live readback and replay.

## Rollback

The live immediate rollback must be resolved at promotion time. The current verified baseline is v7.8.0, but this draft does not hard-code it as a future promotion target. Rollback requires restoring the prior immutable package and authority records. Additive ledger fields remain unused and require no deletion.

## Prohibited in this implementation transaction

No merge to the default branch, tag, GitHub Release, migration apply, System State update, authority activation, production Notion write, or production Todoist write.
