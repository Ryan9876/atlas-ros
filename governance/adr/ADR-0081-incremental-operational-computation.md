# ADR-0081 — Incremental Content-Addressed Operational Computation

## Status

Proposed for v7.4.5 candidate validation.

## Decision

Operational results may be indexed by canonical record identity, source revision, normalized content digest, policy digest, contract version, capability version, dependency digests, authority identity, schema identity, and redaction policy.

Changed nodes and all direct and transitive dependents are recomputed sequentially. Unchanged results are reused only when every identity matches. Missing dependency edges, corrupted indexes, authority changes, schema changes, redaction changes, or other uncertainty force full recomputation.

Persisted indexes are non-authoritative, disposable, bounded, versioned, digest-bound, and rebuildable. They cannot contain credentials, authorization, execution intent, or mutable provider truth treated as permanent state. Full recomputation remains the canonical fallback and periodic verification mechanism.
