# Atlas ROS v6 Breaking Changes

## Removed imports

All `atlas_ros.workflows.*` and `atlas_ros.legacy.*` runtime imports are removed. Use the semantic
replacements in `V6_CANONICAL_CUTOVER_AND_W_RETIREMENT.md`.

## Reconciliation contracts

Reconciliation V2 adds explicit provider-neutral snapshots, field-authority policy version/digest,
structured conflicts, idempotent mutations, integrity-protected checkpoints, exact-plan attended
authorization, operation results, and fail-closed receipts. Historical V1 evidence remains readable
for audit and rollback but is not a v6 application API.

## CLI and configuration

Current commands are semantic. Deprecated numbered command names are removed. Configuration uses
`Execution Reconciliation` rather than a numbered workflow label.

## Behavior

There is no hidden compatibility alias. Intentional differences are limited to stricter rejection
of unknown fields, ambiguous ownership, stale/corrupt checkpoints, incomplete commands, unattended
authorization, and readback mismatch. Objective, Done When, routing, hierarchy, task economy,
provider data formats, and attended execution remain unchanged.
