# Atlas ROS v5.0 Promotion Preparation

## Purpose
Convert intelligence calibration into deterministic promotion evidence without granting promotion authority.

## Required gates
- At least 50 fixed benchmark cases across all intelligence domains.
- Zero critical trust, authority, or unauthorized-action violations.
- Calibration policy passes.
- Full provisioned CI passes Ruff, strict MyPy, tests, coverage, build, clean-wheel validation, and dependency audit.
- A documented solo-maintainer governed review approves the exact release state.
- Ryan explicitly authorizes promotion after publication and readback.

Case-level expert acceptance of benchmark judgments is waived for Atlas ROS
v5.0 by Ryan as the sole user and maintainer. This waiver does not change any
quantitative benchmark threshold or the final governed release review.
Authority: Decision Log record
[`V4D-12`](https://app.notion.com/p/3a6b8344ad2c81cba4a7fc8c951b6335).

## Command
`python scripts/prepare_v500_promotion.py benchmarks/ryan-intelligence-evaluation-set-v1.json calibration-report.json promotion-output`

The builder always emits `promotion_authorized: false`.
