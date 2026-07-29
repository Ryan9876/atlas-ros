# Atlas ROS v7.6.0 Schema and Migration Proposal

## Schema result

Create three dedicated additive data sources under the authoritative Production Databases parent page. Do not modify Universal Inbox, Review Records, or any unrelated database. Exact property names and types are retained in `V760_SCHEMA_PLAN.json`.

The rollback plan is non-destructive: disable v7.6.0, restore v7.5.2 behavior, and leave empty additive data sources unused. Deleting an authorized data source is not part of rollback.

## Initial migration snapshot

The read-only snapshot includes:

- Universal Inbox `Needs Clarification` rows: 0.
- Review `V4V-90`: implementation acceptance evidence, not confirmed Ryan intent evidence.
- Twelve v7.5.2 minimized regression cases: evaluation fixtures, not production intent evidence.

Expected result: create 0, update 0, skip 13. This is the correct fail-closed outcome. The migration does not invent production memory from test data.

## Live migration procedure after exact authorization

1. Re-read live authority and predecessor identity.
2. Verify the authorized target data-source IDs and exact schemas.
3. Capture and digest the exact source snapshot.
4. Re-run the deterministic proposal and compare all digests and counts.
5. Apply only the exact authorized creates or updates.
6. Read back every destination record and digest.
7. Replay migration and verify zero additional creates or updates.
8. Record contradictions, skipped items, and readback receipt.
9. Keep inference disabled until all gates pass.

Any source or count difference invalidates the authorization and requires a new proposal.
