# Atlas ROS v5.0 Promotion Preparation

## Purpose
Convert intelligence calibration into deterministic promotion evidence without granting promotion authority.

## Required gates
- At least 50 fixed benchmark cases across all intelligence domains.
- Zero critical trust, authority, or unauthorized-action violations.
- Calibration policy passes.
- Full provisioned CI passes Ruff, strict MyPy, tests, coverage, build, clean-wheel validation, and dependency audit.
- Independent reviewer approves the benchmark judgments and evidence.
- Ryan explicitly authorizes promotion after publication and readback.

## Command
`python scripts/prepare_v500_promotion.py benchmarks/ryan-intelligence-evaluation-set-v1.json calibration-report.json promotion-output`

The builder always emits `promotion_authorized: false`.
