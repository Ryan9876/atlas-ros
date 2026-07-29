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

## Resolved architecture and policy decisions

1. v7.5 integrates behind a governed feature policy wrapping the existing v6.2 adaptive input pipeline. It does not replace the v6.2 path directly.
2. Confirmed interpretation evidence is stored in Review Records using existing metadata and page content.
3. Historical duplicate-review findings are stored in Review Records and remain read-only and proposal-only.
4. No production Notion schema migration is required for candidate implementation.
5. Contextual familiarity below `0.72` requires clarification when related records exist and completion equivalence is unresolved.
6. Strong evidence requires at least two relevant confirmed interpretations and contextual score at least `0.70`.
7. Confirmed pattern requires at least four confirmed interpretations, at least two explicit user corrections, and contextual score at least `0.85`.
8. Security, compliance, production, architecture, vendor, external commitment, material cost, or irreversible impact overrides familiarity when multiple interpretations remain.

Governed decision: https://app.notion.com/p/3acb8344ad2c81758df3e17da0276687

Architecture/schema review: https://app.notion.com/p/3acb8344ad2c816fbfabd9350a039d58

## Schema-change proposal

No Notion schema was changed. Existing Review Records can hold confirmed interpretations and historical-review proposals. A future additive Universal Inbox migration may be proposed only if Full Validation demonstrates that page content and linked Review Records are insufficient. Any production migration requires separate exact authorization and readback.

## Validation status

- Static and automated CI: pending latest branch/PR workflow result.
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

## Remaining unresolved decisions

None at the architecture-policy level. Validation may surface implementation defects or evidence gaps, but it must not silently change the decisions above.
