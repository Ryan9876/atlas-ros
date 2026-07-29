# ADR-0079 — Runtime Performance Governance

## Status

Proposed for v7.4.5 candidate validation.

## Decision

Runtime performance is measured through versioned, redacted, behavior-neutral contracts. Budgets cover startup, authority initialization, runtime composition, provider reads, snapshot normalization, operational computation, memory, and final validation.

Thresholds must come from measured baselines and observed variance rather than arbitrary targets. Telemetry cannot contain credentials, secrets, authorization payloads, unnecessary provider content, or execution intent. It cannot influence authority, suppress correctness checks, alter command results, or enable autonomous action.

Candidate evidence compares baseline, unoptimized, optimized, full-composition, scoped-composition, full-recomputation, and incremental paths. Unavailable provider latency or byte metrics remain explicitly unmeasured and are never fabricated.
