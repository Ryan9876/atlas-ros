# Atlas ROS v7.5 Release-Candidate Review

## Result

Atlas ROS v7.5 Adaptive Clarification and Intent Learning is ready for exact-package promotion review. It is not authorized for immutable publication or production activation.

## Scope

The candidate implements:

- explicit `related_but_non_equivalent` classification;
- duplicate decisions based on material completion equivalence;
- contextual familiarity and evidence-sensitive clarification;
- focused attended clarification questions;
- confirmed interpretation evidence with current-instruction precedence;
- execution blocking while clarification remains unresolved;
- proposal-only historical duplicate review;
- the ANX centralized-management regression case;
- non-destructive rollback to the v7.4.5 processing path.

## Resolved architecture and policy decisions

1. v7.5 runs behind a governed feature policy wrapping the existing v6.2 adaptive input pipeline.
2. The v6.2 path remains the fallback and rollback path.
3. Confirmed interpretation evidence uses Review Records with existing metadata and page content.
4. Historical duplicate-review findings use Review Records and remain read-only and proposal-only.
5. No production Notion schema migration is required.
6. Contextual familiarity below `0.72` requires clarification when related work exists and completion equivalence is unresolved.
7. Strong evidence requires at least two relevant confirmed interpretations and contextual familiarity at least `0.70`.
8. Confirmed pattern requires at least four confirmed interpretations, at least two explicit user corrections, and contextual familiarity at least `0.85`.
9. Security, compliance, production, architecture, vendor, external commitment, material cost, or irreversible impact overrides familiarity when multiple interpretations remain.

Governed decision: https://app.notion.com/p/3acb8344ad2c81758df3e17da0276687

Architecture/schema review: https://app.notion.com/p/3acb8344ad2c816fbfabd9350a039d58

Exact-package promotion proposal: https://app.notion.com/p/3acb8344ad2c81488c7cf139e6861288

## Exact package identity

- Version: `7.5.0`
- Exact package source commit: `e5b828d40e63e6d3106ae6bddbcc08b48273f74b`
- Full validation run: `30461951342`
- Independent repository CI run: `30461951173`
- Retained evidence artifact: `8728012606`
- Evidence artifact SHA-256: `60f9a02910564ccf066d47136dc910c793b750c43c70ef264fb709dcec660bc1`
- Wheel SHA-256: `037b229c0e0e006202c6cceec916c67313664f1e7ae9a1c2e685bfd10bb729bd`
- Source distribution SHA-256: `e6327b2f77e293cad543c6b1fec1d2c8ceff5b3321a05828f586c5b9ef52660d`
- SPDX SBOM SHA-256: `a7b35c0851bc2a251a4a0e7abe7cff40350493a285b46f1f28bcbeb5b0ce664c`
- Source manifest SHA-256: `560538e715418a80fe2be595489bd419fb036125ff56cdc8e0655049c9ac38ac`
- Full-validation receipt SHA-256: `4b084a6d96324234720a4864eeb25acf2fb65f3c1f62bf0ac5600b0d6ef5970c`
- Build count: `1`

## Validation evidence

The exact package passed:

- repository-wide Ruff and strict MyPy;
- architecture and development-boundary checks;
- 760 automated tests;
- branch-aware coverage above the required 85% threshold;
- adaptive clarification and ANX regression tests;
- deterministic reprocessing and idempotence checks;
- source secret scan with zero findings across 2,169 files;
- locked dependency audits through PyPI and OSV with zero vulnerabilities;
- build-once source and wheel packaging;
- source manifest and SPDX SBOM generation;
- clean installation and verification from both wheel and source distribution;
- checksum validation of published v7.4.5 and v7.4.0 release assets;
- clean restoration installation for Active v7.4.5 and immediate rollback v7.4.0;
- independent general repository CI.

## Governed reviews

- Implementation review: https://app.notion.com/p/3acb8344ad2c81f596f3f4f3859b5347
- Security and privacy review: https://app.notion.com/p/3acb8344ad2c81f982f9e2f9c1be2ce1
- Schema review: https://app.notion.com/p/3acb8344ad2c81b28d32d941951a706e
- Test and validation evidence: https://app.notion.com/p/3acb8344ad2c8178b111d2cc8d6afdd8
- Rollback and restoration review: https://app.notion.com/p/3acb8344ad2c8145a868fbbb689586fa
- Provider-write review: https://app.notion.com/p/3acb8344ad2c81ddbfffda13251b1502
- Release-candidate review: https://app.notion.com/p/3acb8344ad2c8113a401d8cec9e7decb

## Threat, privacy, and failure-mode review

Primary risks were false duplicate suppression, excessive questioning, stale-history overreach, speculative profiling, implicit execution authorization, adapter or reconciliation intent invention, and destructive rollback.

Controls include completion-equivalence comparison, contextual evidence gates, explicit current-instruction precedence, stale and contradictory evidence exclusion, user-correction attribution, provider-write invariants, no Todoist execution while clarification is unresolved, proposal-only historical review, and evidence-preserving rollback.

No inferred psychological trait becomes an authoritative fact. Evidence must be relevant, attributable, sufficiently recent, and conflict-aware.

## Schema review

No production schema change is required. Review Records can hold confirmed interpretations and historical-review proposals using existing fields and page content. No schema property was added, removed, renamed, or modified.

## Provider-write review

- Provider writes: `0`
- Todoist writes: `0`
- Production schema migrations: `0`
- Authority changes: `0`
- Releases or tags published: `0`
- Integration-scope changes: `0`
- Credential actions: `0`
- Messages, email, calendar, or scheduled actions: `0`
- Records deleted: `0`
- Feature enabled by default: `false`

## Rollback review

Rollback disables the v7.5 feature policy and restores the v7.4.5 path. Confirmed user evidence and Review Records are preserved. No record, schema property, or immutable release is deleted or rewritten. Clean restoration of both v7.4.5 and v7.4.0 passed.

## Promotion boundary

The candidate is ready for exact-package promotion review only. Immutable tag or Release publication, merge into production authority, Active release activation, rollback change, Notion System State update, and production feature enablement require separate authorization covering the exact package identity above.

## Unresolved decisions

None.
