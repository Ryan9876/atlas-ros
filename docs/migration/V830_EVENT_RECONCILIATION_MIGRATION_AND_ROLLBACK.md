# v8.3.0 Migration, Cutover, and Restoration

## Baseline

- Active source: v8.2.1 authority and exact immutable package.
- Production ledger: `Execution Reconciliation State`, database `e72c11168cb54d7e8069c7ac9ecb807b`, data source `dc486c5d-c5d2-4386-8a50-d18d1dfb7223`.
- Verified checkpoint: `3aeb8344ad2c8180bdb0c7c8db42b21f`.
- W04 database `ba2518b1-3c97-4a94-8324-414f74ed8830` and data source `afbb753c-3112-4784-9165-f786b503d1f7` are permanently prohibited.

## Additive migration

The Notion ledger schema is unchanged. v8.3 event/policy evidence remains a deterministic versioned JSON envelope in `Notes`. Local/runtime durable tables are additive. Existing v8.2 state keys, comment aliasing, ledger envelope fields, baseline, checkpoint, CLI, and attended ChatGPT paths remain valid.

No historical provider events are backfilled. Cutover requires an exact zero-write inventory, starting checkpoint/sync tokens, monitored event census, digest, and attended migration authorization.

## Cutover gates

1. Validate exact package and immediate rollback.
2. Approve runtime, secrets, identities, scopes, retention, and owner.
3. Enable ingress/planning/backstop in monitor-only; business-provider writes must remain zero.
4. Prove delivery/backstop parity, deduplication, restart recovery, SLOs, and no loops.
5. Activate bounded auto-apply only with exact policy authorization.
6. Read back runtime controls, provider subscriptions, ledger, checkpoint, integration inventory, and authority.

## Restoration

The immediate rollback remains v8.2.1 after a future v8.3 activation. Kill event application first; retain event/receipt evidence; restore the immutable v8.2.1 package and attended policy; verify its reader ignores additive v8.3 runtime tables and envelope keys; verify the same production ledger and prior consistent checkpoint. No restoration path may recreate, rename, query, or write W04.
