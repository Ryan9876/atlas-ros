# Atlas ROS v7.5 Decision Resolution

Status: accepted for release-candidate implementation only.

## Integration

v7.5 runs behind a governed feature policy that wraps the existing `AdaptiveInputProcessingPipelineV62`. The v6.2 path remains the fallback and rollback path. The v7.5 policy may influence classification and clarification only; it cannot authorize execution, write providers, create Todoist objects, or modify reconciliation intent.

## Evidence destination

Confirmed interpretation evidence and proposal-only historical duplicate-review findings are stored as Review Records. This avoids creating a new production evidence database and preserves existing review/audit controls.

## Schema

No production schema migration is required for candidate implementation. Clarification evidence is retained in Review Records content and existing metadata fields. A future Universal Inbox migration is limited to the minimum capture-state fields only if full validation demonstrates that page content and linked Review Records are insufficient.

## Thresholds

- Related records plus contextual familiarity below `0.72`: clarification required.
- Strong evidence: at least two relevant confirmed interpretations and contextual familiarity at least `0.70`.
- Confirmed pattern: at least four relevant confirmed interpretations, at least two explicit user corrections, and contextual familiarity at least `0.85`.
- Minimal or partial evidence never suppresses clarification when the completion boundary is unresolved.
- Security, compliance, production, architecture, vendor, external commitment, material cost, or irreversible impact overrides familiarity when multiple interpretations remain.

## Historical review

Historical duplicate review is read-only and proposal-only. Findings are written as Review Records. No archived capture is reopened, reclassified, or modified without separate exact authorization.

## Rollback

Disable the v7.5 feature policy, restore the v6.2 path, preserve Review Records and user-confirmed evidence, retain any additive fields unused, and verify provider writes remain zero.

## Governed records

- Decision: https://app.notion.com/p/3acb8344ad2c81758df3e17da0276687
- Architecture/schema review: https://app.notion.com/p/3acb8344ad2c816fbfabd9350a039d58
