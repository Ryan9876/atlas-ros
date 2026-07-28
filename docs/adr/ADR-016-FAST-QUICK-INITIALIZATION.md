# ADR-016 — Consolidated Fast Quick Initialization

## Status

Accepted for the Atlas ROS v7.1.1 corrective-release candidate.

## Context

The canonical v7 initialization sequence is correct but an assistant or external caller can incur unnecessary tool discovery, repeated GitHub document reads, full Notion page payloads, and duplicate connector liveness probes. The v7.1.0 warm cache exists but is not connected to bootstrap.

## Decision

Atlas exposes one typed `quick_initialize` operation. It always reads and validates live `AUTHORITY.json`. It may reuse only an authenticated, TTL-bound, source-digest-bound snapshot of the generated Release Index and immutable active-release manifest. It then reads compact System State and Integration Inventory projections live. Successful GitHub and Notion authority reads establish their current read availability; the only additional connector probe is Todoist.

The immutable manifest can declare a stable `collection://` Integration Inventory data-source reference so initialization avoids a discovery-only database fetch. The operation returns a compact non-authoritative receipt and never returns full source documents.

## Failure behavior

Cache absence uses the cold path. Expiration uses a silent cold fallback. Corruption, authentication failure, schema mismatch, or digest mismatch produces a warning and canonical cold fallback. Any authority contradiction, mutable-state disagreement, required-integration problem, or required connector read failure blocks initialization.

## Consequences

Repeated initialization removes two remote GitHub content reads while preserving live authority and mutable-state verification. The design adds no provider writes, dependencies, service, daemon, database, queue, or new source of truth. Production Notion projection activation remains a separate release-controlled transaction.
