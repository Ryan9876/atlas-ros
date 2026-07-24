# Atlas ROS v5.0 Intelligence Evaluation and Calibration Framework

## Purpose

This framework measures the quality of Atlas ROS intelligence outputs instead of only verifying that software gates executed successfully. It evaluates whether recommendations, priority calls, risk predictions, root-cause hypotheses, and learning outputs are correct, calibrated, evidence-backed, explainable, and free from hallucination.

## Core model

The framework separates three objects:

1. **CalibrationCase** — fixed ground-truth scenario with expected label and authority references.
2. **IntelligenceJudgment** — Atlas output for the case, including predicted label, confidence, evidence references, explanation quality, evidence completeness, and hallucination flag.
3. **IntelligenceCalibrationReport** — deterministic aggregate quality report with release-blocking policy checks.

### Confidence semantics

`IntelligenceJudgment.confidence` is the evaluator's confidence that its selected
label is correct. For a recommendation, it is the leading option's share of all
non-negative adjusted option scores. This makes the value comparable with the
binary correctness outcome used by Brier score and expected calibration error.
The corrected mapping is evaluator version `rie-cal-2.1`.

This is intentionally separate from `RecommendationRecord.confidence`, which is
an absolute action-safety score derived from evidence strength, claim strength,
graph support, and decision margin. Calibration must not treat that conservative
safety score as a probability that the selected label is correct. For an
abstention, judgment confidence uses the reasoning trace's uncertainty.

## Metrics

The framework computes:

- Accuracy
- Macro precision
- Macro recall
- Macro F1
- Brier score
- Expected calibration error
- Hallucination rate
- Evidence completeness
- Explanation quality
- Reviewer acceptance rate (advisory unless explicitly enabled by policy)
- Per-domain performance
- Regression against a previous calibration report

## Release gates

Release eligibility is blocked when:

- Overall accuracy falls below policy.
- Macro F1 falls below policy.
- Brier score exceeds policy.
- Expected calibration error exceeds policy.
- Hallucination rate exceeds policy.
- Evidence completeness falls below policy.
- Explanation quality falls below policy.
- Any domain-specific accuracy or calibration gate fails.

Case-level expert acceptance is not a release-blocking gate under the
`rie-calibration-1.1` default policy. Ryan explicitly waived that gate for Atlas
ROS v5.0 as the sole user and maintainer. The policy retains
`require_reviewer_acceptance` so a future release can re-enable it explicitly.
The governing exception is Decision Log record
[`V4D-12`](https://app.notion.com/p/3a6b8344ad2c81cba4a7fc8c951b6335).

## Governance boundary

The framework measures intelligence quality. It cannot promote a release, approve a Candidate, change production authority, or alter learning policy. Generated judgments remain deterministic pipeline-smoke evidence rather than independent accuracy evidence. Waiving case-level expert acceptance does not waive accuracy, F1, Brier, expected-calibration-error, hallucination, evidence-completeness, explanation-quality, domain, or regression gates. Calibration results may be consumed by the Release Control Center as read-only intelligence-health evidence.

## CLI

```bash
atlas intelligence calibrate cases.json judgments.json
atlas intelligence compare-calibration baseline-report.json current-report.json
```

The CLI emits JSON for deterministic ingestion by the Release Validation Workbench and Release Control Center.
