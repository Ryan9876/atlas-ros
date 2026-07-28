# Atlas ROS v7.0.0 Final Release Notes

Atlas ROS v7.0.0 establishes the canonical GitHub-first operating architecture while preserving the attended, read-before-write, and fail-closed safety boundaries of the v6.5 production baseline.

Status: Active production release after exact final-package validation V4V-55, exact-package authorization V4D-39, immutable publication, and independent publication readback V4V-56.

## Authority and initialization

- Adds a typed GitHub authority record with deterministic integrity validation.
- Adds an authority compiler that produces mutually bound authority JSON and a generated human-readable Release Index.
- Makes GitHub canonical for source, architecture, policy, release identity, validation, restoration, and immutable software history.
- Retains the fixed Google Drive Release Index as the initialization bootstrap unless a separate retirement transaction is authorized and verified.
- Requires the fixed Release Index, Notion System State, active GitHub manifest, and manifest-resolved Integration Inventory to agree before initialization succeeds.
- Requires GitHub, Google Drive, Notion, and Todoist as the exact v7 production integration set.

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
- Requires active-v7 readback, verified v6.5 rollback restoration, item-level exclusion review, and a separate exact deletion authorization before any destructive action.
- Does not authorize Drive retirement, historical deletion, or credential revocation.

## Actions cost controls

- Routine pull-request synchronization runs one lean CI job.
- Full dependency security, architecture, documentation, Drive, candidate, exact-artifact, and controller validation run only at governed release milestones.
- Exact-head prerequisites are bound by commit SHA and artifact digest.
- Stale in-progress development runs are canceled.
- Routine evidence uses short retention; final governed evidence uses release-grade retention.

## Production identity

- Active release: `v7.0.0`
- Production source and immutable tag target: `5e480de42b6aeba3c1b5b84384610555f87b2f0e`
- Authorized final source: `a20bfd55ff73fc42addd882ae0211668dca35417`
- Final source SHA-256: `a1ca0114b07b0d6e0080da2a412d68dc4a31870cbd5adfcfa58cd25499032391`
- Final wheel SHA-256: `dd4baa87440fc51c3bc8e845104fbedcd15489de4683eee36f3436632979463d`
- Immediate immutable rollback: Atlas ROS v6.5.0 at `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Historical rollback retained: Atlas ROS v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f`

Publication and authority activation do not expand Todoist scope, enable autonomous execution, retire Drive, delete historical records, change credentials, or authorize scheduling, messaging, email, calendar, or live-network execution.
