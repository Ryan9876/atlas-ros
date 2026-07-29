# ADR-0077 — Provider Read Planning and Coalescing

## Status

Proposed for v7.4.5 candidate validation.

## Decision

The application layer declares all semantically required provider reads before adapter execution and compiles them into `OperationalReadPlanV1`. Identical record reads are deduplicated, overlapping fields and relationships are unioned, pagination remains bounded, and provider batching is used only when supported.

Adapters translate the plan, paginate sequentially, select fields, and return exact receipts. They may not decide evidence necessity, suppress fields, infer state, rank records, or authorize writes. Incomplete or truncated evidence remains explicit and blocks unsafe conclusions or broadens the read scope according to existing policy.
