# Atlas ROS v7.6.0 Feature Implementation Contract

## Purpose

Atlas ROS v7.6.0 becomes the sole governed owner of intent evidence and contextual familiarity. It learns only from attributable, confirmed, relevant, current evidence and provides inspection, correction, retirement, and separately authorized forgetting controls.

## Authoritative predecessor

- Active predecessor: Atlas ROS v7.5.2.
- Immediate rollback during candidate validation: Atlas ROS v7.5.1.
- Accepted v7.5.1 clarification behavior and v7.5.2 evaluation contracts remain unchanged and are consumed through compatibility adapters.
- Current explicit instructions and live authority always outrank learned evidence.

## Required layers

1. Source evidence.
2. Governed intent evidence.
3. Context and scope keys.
4. Freshness, correction, contradiction, and retirement state.
5. Inference-eligibility decisions.
6. Active intent-memory index.
7. Inspection views.
8. User-control receipts.
9. Content-free forgetting tombstones where legally or operationally required.

Universal Inbox remains operational state and is not the complete historical learning store.

## Required contracts

- `GovernedIntentEvidenceV1`
- `IntentContextKeyV1`
- `IntentScopeV1`
- `IntentConfirmationV1`
- `IntentCorrectionV1`
- `IntentContradictionV1`
- `IntentFreshnessPolicyV1`
- `IntentEligibilityDecisionV1`
- `IntentMemoryIndexV1`
- `IntentInspectionViewV1`
- `IntentUserControlReceiptV1`
- `IntentForgettingTombstoneV1`

All contracts are frozen, versioned, extra-field rejecting, and deterministically digestible.

## Evidence precedence

1. Ryan's explicit instruction in the current interaction.
2. Live authoritative records.
3. Confirmed, relevant, current governed intent evidence.
4. Consistent attributable historical evidence.
5. General inference, which is not stored as governed evidence.

Stale, contradictory, retired, forgotten, unrelated, unconfirmed, speculative, or low-confidence evidence cannot independently control consequential classification.

## Feature policy

The release is disabled by default. Inspection can be enabled without inference. Scope-level and evidence-level disables are supported. Inference falls back to accepted v7.5.2 behavior unless an exact active decision is eligible under the current context and policy.

## Persistence boundary

The exact schema proposal creates three additive data sources under the existing Production Databases page:

- Governed Intent Evidence.
- Active Intent Memory Index.
- Intent User Control Receipts.

No existing data source is modified. Universal Inbox and Review Records remain unchanged. Production schema application requires separate exact authorization and readback.

## Migration boundary

Migration is attended, deterministic, idempotent, and provider-write free in dry-run mode. It reads predecessor evidence without rewriting it. Synthetic fixtures, implementation reviews, speculative interpretations, stale evidence, contradictory evidence, retired evidence, unattributable evidence, and incomplete evidence are skipped.

## Definition of Done

1. All required contracts and machine-readable schemas exist.
2. Scope isolation prevents cross-user, cross-project, cross-domain, and sensitive-context leakage.
3. Current instructions and live authority override learned evidence immediately.
4. Correction preserves original evidence and disables the incorrect interpretation.
5. Retirement excludes evidence while preserving audit provenance.
6. Forgetting cannot be claimed without exact authorization, provider mutation evidence, and live readback.
7. Active indexes exclude stale, contradictory, retired, and forgotten evidence.
8. Compatibility adapters preserve predecessor source references and digests.
9. Migration replay is deterministic and creates no duplicates.
10. Schema and migration proposals produce zero provider writes.
11. Disabled-feature behavior falls back to v7.5.2.
12. Targeted and full tests, lint, strict typing, architecture checks, privacy review, secret scan, dependency audits, clean installs, restoration, and checksums pass.
13. Source and wheel are built exactly once and retained.
14. Candidate validation stops before publication, authority activation, schema application, or migration.
