# Atlas ROS v7.1.1 Fast Initialization Operator Guide

## Quick path

Call `quick_initialize` once with configured GitHub authority, Notion dynamic-state, Todoist liveness, and optional warm-cache adapters. Treat the returned receipt as non-authoritative evidence; the live authorities remain canonical.

## Expected reads

Cold path: live authority, generated Release Index, immutable manifest, compact System State, direct Integration Inventory query, and one Todoist probe.

Warm path: live authority, cached-and-revalidated Release Index and manifest, compact System State, direct Integration Inventory query, and one Todoist probe.

Google Drive is never part of either path.

## Recovery

- Cache unavailable or expired: continue through the cold path.
- Cache rejected: record the warning and continue through the cold path.
- GitHub, Notion, Todoist, digest, schema, authority, rollback, workspace, or integration contradiction: stop and return `INITIALIZATION_BLOCKED`.
- Never infer readiness from a prior receipt.

## Production activation prerequisite

Before v7.1.1 promotion, configure the compact System State projection and direct Integration Inventory query in the production adapter through a separately authorized, readback-verified transaction. Do not change Notion authority records during candidate implementation.
