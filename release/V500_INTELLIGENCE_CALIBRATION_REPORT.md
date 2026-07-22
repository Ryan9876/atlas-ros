# Atlas ROS v5.0 — Intelligence Evaluation and Calibration Framework

Status: Development evidence only. Not a Candidate and not production authority.

## Implemented

- Fixed calibration-case contract
- Intelligence-judgment contract
- Per-domain and overall scoring
- Accuracy, macro precision, macro recall, macro F1
- Brier score and expected calibration error
- Hallucination-rate gate
- Evidence-completeness gate
- Explanation-quality gate
- Reviewer-acceptance capture
- Deterministic report fingerprint
- Regression comparison between calibration reports
- CLI support for calibration and report comparison
- Release Control Center read-only integration for intelligence-health panels

## Boundary

This framework evaluates intelligence quality only. It cannot approve a Candidate, authorize promotion, alter production authority, or self-modify release policy.
