# ADR-0082 — Adaptive Clarification and Intent Learning

## Status

Proposed for Atlas ROS v7.5 release-candidate validation. Production publication, schema migration, and authority activation remain separately authorized.

## Decision

Introduce a deterministic, provider-neutral clarification decision contract that distinguishes duplicate work from related but non-equivalent work and materially distinct outcomes. Duplicate classification requires equivalence across all material completion dimensions. Unresolved material ambiguity preserves the capture and blocks execution routing until attended clarification is confirmed.

## Trust and evidence

Clarification is a normal reasoning mechanism. Context familiarity is multidimensional and request-specific. Confirmed corrections are high-value attributable evidence; current explicit intent and live authority always outrank history. Psychological inference and speculative profiling are prohibited.

## Security and privacy review

- No inferred psychological traits become authoritative facts.
- Evidence must be attributable, relevant, recent, and conflict-aware.
- Clarification output cannot authorize execution or provider writes.
- Consequential ambiguity involving security, compliance, production, architecture, cost, vendors, or external commitments increases clarification.
- Telemetry and evidence must be redacted under existing policy.

## Failure modes and controls

| Failure mode | Control |
|---|---|
| Semantic overlap suppresses distinct work | Completion-equivalence test and `related_but_non_equivalent` classification |
| Excessive questioning | Evidence levels and contextual familiarity; direct inference only for low-risk reversible cases |
| Over-learning from history | Current instruction precedence; stale, contradictory, and unrelated evidence excluded |
| Clarification creates implicit execution | `todoist_write_allowed=false`, `provider_writes=0`, and model validation |
| Adapter or reconciliation invents intent | Existing adapter/planning/reconciliation authority boundaries preserved |
| Historical duplicates are rewritten | Read-only/proposal-only review; no automatic reopen |
| Rollback destroys evidence | Policy rollback preserves responses, records, and additive fields |

## Schema decision

No production schema change is authorized or applied by this candidate. A minimal additive proposal is documented for Universal Inbox and Review Records. Exact data-source IDs, property types, migration statements, and rollback readback must be resolved from live schemas before a separately authorized production migration.

## Restoration

Restore v7.4.5 behavior, preserve clarification evidence, leave any separately approved additive fields unused, and verify zero provider writes. Immutable releases and historical records remain unchanged.
