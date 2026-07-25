# Atlas ROS v6 Rollback Guide

Prospective immediate rollback: immutable Atlas ROS v5.6.0.

## Preconditions

- Verify the published v5.6.0 release and its checksums.
- Install v5.6.0 in a clean environment without v6 source or historical Drive folders.
- Preserve provider records; v6 makes no irreversible provider-data migration.
- Preserve the last verified reconciliation checkpoint and event identities.

## Procedure

1. Stop attended v6 application before starting another mutation group.
2. Retain the v6 receipt, conflict list, checkpoint, and recovery instructions.
3. Install the immutable v5.6 package and verify both planning and orchestration benchmarks.
4. Restore v5.6 configuration and semantic entrypoints; its compatibility interfaces return only
   with that package.
5. Read provider state from the preserved checkpoint before any retry.
6. Ignore v2-only local evidence fields or transform the additive checkpoint envelope using the
   packaged downgrade reader.
7. Resume attended operation only after readback matches.

Rollback does not require v6 source, v6 documentation, or historical Drive release folders.
