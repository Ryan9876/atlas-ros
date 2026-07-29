# Atlas ROS v7.5 Release-Candidate Review

## Scope

Adaptive Clarification and Intent Learning with explicit `related_but_non_equivalent` classification, completion-equivalence duplicate rules, contextual familiarity, evidence-sensitive clarification, clarification evidence, execution gating, and the ANX centralized-management regression case.

## Implementation plan

1. Resolve live v7.4.5 authority and v7.4.0 rollback.
2. Add provider-neutral typed decision contracts and deterministic classification.
3. Add regression and boundary tests.
4. Document architecture, threat model, schema proposal, runbook behavior, and rollback.
5. Run repository CI and full non-publishing validation.
6. Build once, checksum-bind the exact candidate, validate clean installation and v7.4.5 restoration.
7. Record review evidence and stop for exact-package promotion authorization.

## Implemented candidate increment

- Completion-dimension equivalence model.
- Relationship classifications including related but non-equivalent.
- Context-specific familiarity and consequence assessment.
- Evidence levels: minimal, partial, strong, confirmed pattern.
- User-correction weighting with stale/contradictory evidence exclusion.
- Capture preservation and focused clarification question generation.
- Hard execution boundary: Todoist disallowed and provider writes fixed at zero during clarification.
- Deterministic ANX regression coverage.
- Non-destructive historical review and rollback design.

## Threat and failure-mode analysis

See ADR-0082. Primary risks are false duplicate suppression, over-questioning, stale-history overreach, implicit execution authorization, privacy-invasive learning, and destructive rollback. Controls are deterministic completion equivalence, contextual evidence gates, current-instruction precedence, provider-write invariants, proposal-only historical review, and evidence-preserving rollback.

## Schema-change proposal

No Notion schema was changed. The minimum additive proposal is documented in `docs/architecture/V750_ADAPTIVE_CLARIFICATION_AND_INTENT_LEARNING.md`. Production application requires exact migration authorization and schema readback.

## Validation status

- Static and automated CI: pending branch/PR workflow result.
- Full non-publishing validation: pending.
- Clean-install package validation: pending.
- v7.4.5 restoration: pending.
- Provider writes during implementation planning: 0.
- Notion schema writes: 0.
- Todoist writes: 0.
- Messages/calendar/scheduling: 0.
- Records deleted: 0.
- Authority changes: 0.

## Exact package identity

Not yet available. Candidate source commit, artifact ID, source/wheel/SBOM/source-manifest digests, and build count must be populated only from successful build-once validation evidence.

## Promotion boundary

This candidate is not production ready until all mandatory validation, packaging, restoration, security, schema, provider-write, and release-review gates pass. Do not publish a tag or Release, change Active authority, change rollback, or update Notion System State without separate exact-package authorization.

## Unresolved decisions

1. Final additive Notion field placement and types after live schema-by-schema review.
2. Whether v7.5 integrates directly into the v6.2 input pipeline in this release or first lands as an isolated governed capability behind a feature policy.
3. Exact confidence thresholds and policy-owned consequentiality weights after fixture and operational calibration.
4. Location and retention policy for confirmed interpretation evidence.
5. Whether historical duplicate review proposals are stored in Review Records or a dedicated operational evidence store.
