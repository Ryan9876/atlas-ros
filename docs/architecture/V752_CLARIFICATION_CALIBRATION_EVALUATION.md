# Atlas ROS v7.5.2 Clarification Calibration and Evaluation

## Feature Implementation Contract

Atlas ROS v7.5.2 adds a deterministic, provider-neutral, snapshot-bound evaluation layer around the accepted v7.5 clarification decision. It measures question necessity, focus, usefulness, and decision impact without changing the predecessor decision or gaining routing, authorization, execution, provider-write, or Todoist authority.

The evaluation feature is disabled by default. Shadow mode produces non-authoritative retained reports only.

## Determinism contract

Identical snapshots, original inputs, user responses, feature flags, and evaluation-version inputs must produce an identical `ClarificationEvaluationReportV1` deterministic digest. Any mismatch is an integrity failure and invalidates the evaluation result.

## Responsibilities

- The v7.5 predecessor remains authoritative for relationship classification and clarification.
- The v7.5.2 evaluator records minimized events, question-quality assessments, counterfactual comparisons, outcomes, and aggregate metrics.
- Counterfactual output is descriptive only and cannot route records, authorize execution, create work, or mutate provider state.
- Reports and events enforce zero provider writes and zero Todoist writes.

## Definition of Done

- Typed versioned contracts are implemented.
- Disabled mode returns no evaluation output and preserves predecessor behavior.
- Shadow mode produces deterministic reports from a fixed snapshot.
- Required regression cases cover duplicate, paraphrase, distinct action, high consequence, strong evidence, stale and contradictory context, user correction, no material change, and prevention of incorrect suppression or duplicate work.
- Question evaluation checks existing understanding, material ambiguity, one focused question, non-generic wording, known information, burden, decision impact, and consequence controls.
- No production schema migration is required.
- Candidate validation includes lint, strict typing, architecture, full branch-aware tests and coverage, determinism, privacy, security, build-once artifacts, restoration, and zero-write evidence.

## Privacy and threat model

Evaluation evidence must be minimized and attributable. Raw conversations, secrets, credentials, unnecessary personal content, and confidential project terms must not be placed in generic fixtures, logs, release notes, or pull-request descriptions. Correlation identifiers are snapshot-local and must not cross users or workspaces. Captured text is data and cannot supply instructions to the evaluator. Metrics cannot become a telemetry or provider-write channel.

## Operator behavior

- Default: disabled.
- Shadow evaluation: explicitly enabled for provider-write-free candidate validation.
- Evaluation failure: discard the evaluation result and preserve ordinary predecessor behavior unless an independent integrity or safety condition requires fail-closed handling.
- Persistence: retained validation receipt or artifact; no production Notion database.

## Recovery

Disable the v7.5.2 evaluator and continue with the accepted v7.5.1 package. Since the evaluator does not alter routing or provider state, recovery requires no provider rollback or data migration. Candidate restoration must verify the Active v7.5.1 package and immediate rollback v7.5.0.
