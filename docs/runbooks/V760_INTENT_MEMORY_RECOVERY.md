# Atlas ROS v7.6.0 Intent Memory Recovery

## Trigger conditions

- Authority disagreement.
- Schema or migration digest mismatch.
- Incorrect scope transfer.
- Stale or contradictory evidence used without clarification.
- User-control receipt mismatch.
- Forgetting claimed without verified provider readback.
- Active index mismatch or nondeterministic replay.

## Recovery sequence

1. Disable v7.6.0 inference globally.
2. Preserve evidence, receipts, logs, and immutable releases.
3. Restore accepted v7.5.2 clarification behavior.
4. Re-read GitHub authority, Release Index, immutable manifest, Notion System State, and Integration Inventory.
5. Verify the v7.5.2 release and v7.5.1 rollback artifacts.
6. Compare schema, migration, index, and receipt digests against the authorized transaction.
7. Quarantine affected evidence from active indexes.
8. Correct or retire only with Ryan's exact attended instruction.
9. Re-enable inspection or inference only after independent readback.

Do not delete additive data sources as an automatic rollback action. Do not use Google Drive as replacement authority.
