# Atlas ROS v7.0.0rc1 Candidate Release Notes

Atlas ROS v7.0 establishes the candidate foundation for a canonical, GitHub-first operating architecture while retaining the attended and fail-closed safety boundaries of the active v6.5 production release.

## Authority and initialization

- Adds a typed GitHub authority record with deterministic integrity validation.
- Adds a staged authority compiler that produces mutually bound authority JSON and a generated human-readable Release Index.
- Replaces the future v7 Google Drive bootstrap with GitHub authority, while preserving the current v6.5 bootstrap until promotion.
- Requires GitHub authority, the immutable release manifest, Notion System State, and the Integration Inventory to agree before initialization succeeds.
- Requires GitHub, Notion, and Todoist as the exact v7 production integration set; Google Drive cannot be a required v7 initialization authority.

## Runtime architecture

- Adds declarative architecture, capability, contract, and release-policy catalogs.
- Adds the v7 runtime kernel and canonical coordinator foundation.
- Adds stable capture and pipeline-run contracts with digest-bound lineage.
- Adds fail-closed policy compilation and immutable policy snapshots.

## Attended execution

- Adds immutable authorized execution plans.
- Enforces canonical operation order, unique operation IDs, unique idempotency keys, and plan-digest integrity.
- Adds a provider-neutral execution port.
- Executes only the exact authorized plan.
- Requires independent readback for every provider write.
- Produces immutable transaction receipts and rejects adapter substitution or readback mismatch.

## Drive cutover and historical cleanup

- Limits v7 promotion migration to the fixed current Drive Release Index bootstrap and its checksum-equivalent GitHub target.
- Removes pre-v6 package-by-package migration, hashing, and validation from the v7 promotion path.
- Adds a checksum-bound, non-authorized plan for the single 92-folder historical subtree containing versions below v6.
- Preserves every v6.x and newer release outside the historical deletion scope.
- Requires v7 activation, v7 post-promotion readback, verified v6.5 rollback restoration, item-level exclusion review, and a separate exact deletion authorization before any destructive action can be prepared.
- Records zero provider writes and zero destructive actions during candidate validation.

## Governance

- Corrects mutable governance records without changing production authority.
- Moves current Capture Service guidance to immutable GitHub documentation.
- Keeps production at v6.5.0 with v6.2.0 as immediate immutable rollback until a separately authorized v7 promotion completes.

## Candidate limitations

This candidate is not production-authorized. It cannot publish a final release, create or move the final `v7.0.0` tag, activate GitHub authority, retire Google Drive, delete historical Drive content, change integration scope, or perform provider writes during validation.
