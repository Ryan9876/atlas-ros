# Atlas ROS v5.0 Intelligence Evaluation and Calibration Framework

## Purpose

This framework measures the quality of Atlas ROS intelligence outputs instead of only verifying that software gates executed successfully. It evaluates whether recommendations, priority calls, risk predictions, root-cause hypotheses, and learning outputs are correct, calibrated, evidence-backed, explainable, and free from hallucination.

## Core model

The framework separates three objects:

1. **CalibrationCase** — fixed ground-truth scenario with expected label and authority references.
2. **IntelligenceJudgment** — Atlas output for the case, including predicted label, confidence, evidence references, explanation quality, evidence completeness, and hallucination flag.
3. **IntelligenceCalibrationReport** — deterministic aggregate quality report with release-blocking policy checks.

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
- Reviewer acceptance rate
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
- Any case lacks explicit expert reviewer acceptance or is rejected by its reviewer.
- Any domain-specific accuracy or calibration gate fails.

## Governance boundary

The framework measures intelligence quality. It cannot promote a release, approve a Candidate, change production authority, or alter learning policy. Generated judgments are deterministic pipeline-smoke evidence, not independent accuracy evidence; every case requires explicit expert reviewer acceptance under the default release policy. Calibration results may be consumed by the Release Control Center as read-only intelligence-health evidence.

## CLI

```bash
atlas intelligence calibrate cases.json judgments.json
atlas intelligence compare-calibration baseline-report.json current-report.json
```

The CLI emits JSON for deterministic ingestion by the Release Validation Workbench and Release Control Center.
