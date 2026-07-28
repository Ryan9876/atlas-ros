# Atlas ROS v7.0.0 Final Release Notes

Atlas ROS v7.0 establishes the canonical GitHub-first operating architecture while preserving the attended, read-before-write, and fail-closed safety boundaries of the active v6.5 production release.

## Authority and initialization

- Adds a typed GitHub authority record with deterministic integrity validation.
- Adds an authority compiler that produces mutually bound authority JSON and a generated human-readable Release Index.
- Moves v7 initialization authority from the legacy Google Drive bootstrap to GitHub after separately authorized promotion and readback.
- Requires GitHub authority, the immutable release manifest, Notion System State, and the manifest-resolved Integration Inventory to agree before initialization succeeds.
- Requires GitHub, Notion, and Todoist as the exact v7 production integration set.

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
- Keeps pre-v6 package history outside the v7 promotion critical path.
- Retains the checksum-bound, non-authorized plan for the single 92-folder historical subtree containing versions below v6.
- Preserves every v6.x and newer release outside the historical deletion scope.
- Requires v7 activation, post-promotion readback, verified v6.5 rollback restoration, item-level exclusion review, and a separate exact deletion authorization before any destructive action.

## Actions cost controls

- Routine pull-request synchronization runs one lean CI job.
- Full dependency security, architecture, documentation, Drive, candidate, exact-artifact, and controller validation run only at governed release milestones.
- Exact-head prerequisites are bound by commit SHA and artifact digest.
- Stale in-progress development runs are canceled.
- Routine evidence uses short retention; final governed evidence uses release-grade retention.

## Final-package boundary

The final `7.0.0` package may be built and validated without changing production. Publication, the immutable `v7.0.0` tag, authority activation, Drive retirement, historical deletion, integration-scope changes, and provider writes remain blocked until Ryan separately authorizes the exact validated package.
