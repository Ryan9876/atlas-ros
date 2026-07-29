# Atlas ROS v7.5.2 Feature Implementation Contract

## Purpose

Atlas ROS v7.5.2 evaluates the accepted v7.5 adaptive-clarification capability without changing authoritative clarification, routing, execution, provider-write, or Todoist behavior.

## Scope

The implementation is provider-neutral, deterministic, snapshot-bound, disabled or shadow-only by default, and unable to route records, authorize execution, create work, or mutate production data.

## Authoritative predecessor

- Active predecessor: Atlas ROS v7.5.1.
- Clarification authority: accepted v7.5 contracts and policy.
- v7.5.2 references predecessor identifiers and decisions; it does not redefine completion equivalence, relationship classification, familiarity, consequence, clarification, provider-write, or Todoist rules.

## Determinism contract

Identical snapshots, user responses, feature flags, and evaluation-version inputs must produce an identical `ClarificationEvaluationReportV1` deterministic digest.

## Required contracts

- `ClarificationEventV1`
- `ClarificationEvaluationCaseV1`
- `CounterfactualDecisionV1`
- `QuestionQualityAssessmentV1`
- `ClarificationOutcomeV1`
- `ClarificationMetricsV1`
- `ClarificationEvaluationReportV1`

The retained candidate must include machine-readable JSON schemas for all seven contracts.

## Required metrics

The deterministic baseline report records counts and bounded rates for:

- false duplicate and false separate classifications;
- user corrections and clarification frequency;
- one-question resolutions, repeated questions, and questions with no material change;
- prevented task suppression and prevented duplicate task creation;
- confirmed-pattern reuse;
- clarification avoided because of strong evidence; and
- clarification reintroduced after a material context change.

Observed evidence may support threshold recommendations, but v7.5.2 does not create or activate acceptance thresholds.

## Runtime boundaries

When disabled, predecessor behavior is unchanged. When enabled in shadow evaluation:

- predecessor decisions remain authoritative;
- evaluation cannot alter classification, routing, destination, or execution intent;
- counterfactual decisions remain non-authoritative and execution-inert;
- provider writes and Todoist writes remain zero;
- evaluation failures do not block predecessor behavior unless an independent integrity or safety rule requires fail-closed handling; and
- repeated evaluation of identical inputs produces the same report and digest.

## Privacy and security

Evaluation evidence must be minimized, attributable, and redacted. Raw conversations, secrets, credentials, unnecessary personal data, and confidential project terms must not enter public logs, release notes, generic fixtures, or PR descriptions.

The candidate must retain a data-minimization receipt, secret-scan result, dependency-audit results, source manifest, SPDX SBOM, and zero-provider-write receipt.

## Candidate package controls

The controlled candidate workflow must:

1. bind to one exact frozen source commit;
2. build one retained source distribution and wheel;
3. verify both artifacts through clean installations and runtime identity checks;
4. restore and verify the live Active release and immediate rollback from their published artifacts;
5. generate a deterministic baseline report and contract schema bundle;
6. generate package, evidence, and nested SHA-256 checksum files;
7. retain the exact candidate package and evidence as one workflow artifact; and
8. stop before merge, publication, tagging, or authority activation.

## Definition of Done

1. Typed versioned contracts validate provider-write-free, execution-inert records.
2. Evaluation wraps accepted v7.5 decisions without redefining them.
3. Question-quality assessment covers focus, known context, ambiguity, burden, decision impact, consequence, and reversibility.
4. Twelve required regression fixtures are minimized, attributable, privacy-checked, and mapped to predecessor references.
5. Deterministic replay and deterministic report-digest tests pass.
6. Disabled-feature predecessor equivalence tests pass.
7. Provider-write and Todoist-write boundary tests pass.
8. All required counts and rates are present in the baseline report.
9. Baseline recommendations derive from observed evidence without activating invented thresholds.
10. Contract schemas, baseline report, minimization receipt, package index, validation receipt, SPDX SBOM, source manifest, secret scan, dependency audits, and nested checksums are retained.
11. Source distribution and wheel identify version 7.5.2 and pass clean-install verification.
12. Active v7.5.1 and immediate rollback v7.5.0 restoration checks pass.
13. Exact retained build count is one.
14. No production Notion schema migration is required.
15. Candidate validation produces zero-provider-write and zero-Todoist-write receipts and stops before publication or authority activation.
