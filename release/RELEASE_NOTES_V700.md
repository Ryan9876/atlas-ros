# Atlas ROS v7.0.0 Release Notes

Atlas ROS v7.0 establishes the canonical, GitHub-first operating architecture while retaining the attended and fail-closed safety boundaries of the active v6.5 production release until separately authorized promotion.

## Authority and initialization

- Adds a typed GitHub authority record with deterministic integrity validation.
- Adds an authority compiler that produces mutually bound authority JSON and a generated human-readable Release Index.
- Prepares replacement of the Google Drive bootstrap with GitHub authority while preserving the current v6.5 bootstrap until promotion and verified readback.
- Requires GitHub authority, the immutable release manifest, Notion System State, and the manifest-resolved Integration Inventory to agree before initialization succeeds.
- Requires GitHub, Notion, and Todoist as the exact v7 production integration set; Google Drive is transitional and is not a required v7 runtime integration.

## Runtime architecture

- Adds declarative architecture, capability, contract, and release-policy catalogs.
- Adds the v7 runtime kernel and canonical coordinator.
- Adds stable capture, reasoning, execution, and pipeline-run contracts with digest-bound lineage.
- Adds fail-closed policy compilation and immutable policy snapshots.

## Attended execution

- Adds immutable authorized execution plans.
- Enforces canonical operation order, unique operation IDs, unique idempotency keys, and plan-digest integrity.
- Adds provider-neutral execution ports and exact provider payload contracts.
- Executes only the exact authorized plan.
- Requires independent readback for every provider write.
- Produces immutable transaction receipts and rejects adapter substitution or readback mismatch.

## Drive cutover and historical cleanup

- Limits v7 promotion migration to the fixed current Drive Release Index bootstrap and its checksum-equivalent GitHub target.
- Excludes pre-v6 package-by-package migration from the v7 promotion path.
- Retains a checksum-bound, non-authorized plan for the single 92-folder historical subtree containing versions below v6.
- Preserves every v6.x and newer release outside the historical deletion scope.
- Requires v7 activation, post-promotion readback, verified v6.5 rollback restoration, item-level exclusion review, and a separate exact deletion authorization before any destructive action.

## Validation and release controls

- Separates lean development CI from full dependency-security and exact-package validation.
- Requires PyPI and OSV advisory audits for the exact final source.
- Requires package and nested-evidence checksums, clean installation, rollback restoration, integration readiness, performance validation, and non-publishing final-controller validation.
- Cancels stale development runs and retains final governed evidence for release-grade retention.
- Keeps publication, final tag creation, authority activation, Drive retirement, credential changes, and provider writes blocked until exact-package authorization.

## Governance

- Corrects mutable governance records without rewriting historical release evidence.
- Moves current Capture Service guidance to immutable GitHub documentation.
- Keeps production at v6.5.0 with v6.2.0 as immediate immutable rollback until a separately authorized v7 promotion completes.

## Production boundary

This final package may be built and validated without changing production. Publishing `v7.0.0`, creating the immutable tag, activating GitHub authority, switching production, retiring Google Drive, deleting historical content, changing credentials, or expanding provider scope requires a separate exact-package production authorization and verified post-publication readback.