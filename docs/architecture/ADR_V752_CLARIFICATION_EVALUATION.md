# ADR — Atlas ROS v7.5.2 Clarification Evaluation

## Decision

Implement clarification calibration as a provider-neutral, snapshot-bound wrapper over the accepted v7.5 clarification decision. The predecessor decision remains authoritative. v7.5.2 produces only non-authoritative retained evaluation artifacts.

## Boundaries

- Disabled by default; shadow-only when enabled.
- No routing, destination, execution-intent, provider-write, Todoist-write, messaging, scheduling, credential, schema, or live-network authority.
- Counterfactual output is evidence for evaluation only and cannot be consumed by execution adapters.
- Identical snapshots, responses, flags, and evaluation version produce identical report digests.

## Persistence

Use retained validation artifacts and receipts. No production Notion schema migration is required.

## Failure behavior

Evaluation errors do not block accepted predecessor behavior unless an independent integrity or safety control requires fail-closed handling.
