# v8.2.1 Production Ledger Migration Plan

## Preconditions

- Re-read GitHub authority, Release Index, immutable manifest, System State, and Integration Inventory.
- Confirm W04 database `ba2518b1-3c97-4a94-8324-414f74ed8830` remains deleted.
- Confirm exact authorization for the ledger schema, then record one immutable UTC cutover timestamp.

## Authorized production sequence

1. Create `Execution Reconciliation State` beneath Production Databases with the ADR-0083 schema.
2. Read back the database and data-source identities, title, properties, select options, and lifecycle state.
3. Enumerate mapped Action Records, their parent tasks and subtasks, and every current comment before cutover.
4. Generate and authorize an exact source-inventory and baseline plan digest.
5. Write one `Processed Event` record per pre-cutover comment, read each back, then verify inventory count,
   canonical/alias uniqueness, and source digests.
6. Create exactly one `todoist:checkpoint` only after the complete readback passes.
7. Replay the exact baseline and verify zero writes or provider mutations.
8. Update configuration and authority only after exact package authorization and post-publication verification.

## Failure handling

Any incomplete write, source-digest mismatch, ambiguous identity, or readback failure stops execution before
checkpoint creation. Preserve successful evidence; produce a partial-failure receipt. Do not update Todoist,
Action Records, Execution Steps, Universal Inbox, or historical W04 records.
