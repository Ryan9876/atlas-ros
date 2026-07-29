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

## Runtime boundaries

When disabled, predecessor behavior is unchanged. When enabled in shadow evaluation:

- predecessor decisions remain authoritative;
- evaluation cannot alter classification, routing, destination, or execution intent;
- provider writes and Todoist writes remain zero;
- evaluation failures do not block predecessor behavior unless an independent integrity or safety rule requires fail-closed handling;
- repeated evaluation of identical inputs produces the same report and digest.

## Privacy and security

Evaluation evidence must be minimized and redacted. Raw conversations, secrets, credentials, unnecessary personal data, and confidential project terms must not enter public logs, release notes, generic fixtures, or PR descriptions.

Counterfactual outputs are explicitly non-authoritative and must not be consumed by routing or execution adapters.

## Definition of Done

1. Typed versioned contracts validate provider-write-free, execution-inert records.
2. Evaluation engine wraps accepted v7.5 decisions without redefining them.
3. Question-quality assessment covers focus, known context, ambiguity, burden, decision impact, consequence, and reversibility.
4. Required regression fixtures are minimized and attributable.
5. Deterministic replay and deterministic report-digest tests pass.
6. Disabled-feature predecessor equivalence tests pass.
7. Provider-write and Todoist-write boundary tests pass.
8. Baseline reporting recommends thresholds from evidence rather than inventing them.
9. No production Notion schema migration is required.
10. Candidate validation produces a zero-provider-write receipt and stops before publication or authority activation.
