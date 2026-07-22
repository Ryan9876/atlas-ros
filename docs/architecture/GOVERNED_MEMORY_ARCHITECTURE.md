# Governed Memory Architecture

## Purpose

Milestone 4 turns immutable Canonical Intelligence Records into a policy-governed memory substrate. Memory is metadata over canonical records; it never mutates the underlying evidence, context, prediction, recommendation, decision, or learning record.

## Tiers

- **Working:** short-lived context for the current task or session.
- **Episodic:** time-bounded events, predictions, and recommendations.
- **Semantic:** durable decisions and verified learning events.
- **Governed:** non-expiring, verified evidence from primary, authoritative-application, or governed-internal sources.

## Retrieval policy

Retrieval is deterministic and filters before ranking. Privacy, expiration, tier eligibility, and unresolved conflict controls are non-compensatory gates. Eligible memories are ranked by authority, record confidence, salience, and exponential recency decay. Stable identifier ordering resolves ties.

## Retention and expiration

Retention decisions are derived from record kind, lifecycle, source authority, validation status, and confidence. Expiration deletes memory metadata only; canonical records remain append-only for audit and reproducibility.

## Conflict handling

Conflicting memories are hidden from default retrieval until explicitly resolved. Resolution identifies the superseding memory while preserving the superseded record and its audit trail.

## Privacy boundary

Every memory has an explicit privacy class. Retrieval callers must provide allowed classes. Evaluation reports privacy leakage as a blocking validity failure.

## Evaluation

The memory evaluator measures reference resolvability, integrity, expiration, conflict state, and privacy compliance. A memory corpus is valid only when all references resolve, hashes verify, and no memory exceeds the caller's privacy boundary.
