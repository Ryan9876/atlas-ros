# Atlas ROS v5.0.0rc1 Current Candidate Validation Report

Validation window: 2026-07-22 America/Detroit / 2026-07-23 UTC

Status: **Implementation validated; not yet a release Candidate.**

This report covers the uploaded authoritative working copy on
`atlas/release-v500-candidate`. It does not authorize a commit, push, Candidate
declaration, or production promotion. Atlas ROS v4.5.3 remains Active and v4.5.2
remains the immediate immutable rollback.

## Repository and architecture result

- Audited 55 package modules and 111 unique internal package-level import edges.
- Reconciled the uploaded branch with the observable GitHub branch content; the
  only unique GitHub source change was Ruff-oriented formatting in
  `scripts/prepare_v500_promotion.py`.
- Removed the orchestration circular self-import.
- Preserved the reasoning/governance boundary: reasoning owns recommendation
  generation, governance owns policy disposition, and the pipeline is a facade.
- Completed explicit inference-to-option targeting and append-only persistence of
  inference, recommendation, policy-evaluation, and decision-governance records.
- Verified all 106 public `atlas_ros.intelligence` exports resolve uniquely.
- Synchronized all seven runtime record-reference schema enums with the thirteen
  canonical `RecordKind` values.

## Current validation evidence

| Gate | Result | Evidence |
|---|---|---|
| Ruff | PASS | Entire repository |
| Strict MyPy | PASS | 55 source files |
| Full regression suite | PASS | 239 tests |
| Branch coverage | PASS | 89.05%, threshold 85% |
| Source and wheel build | PASS | `atlas-ros==5.0.0rc1` |
| Clean-wheel install and packaged-policy smoke | PASS | Fresh Python 3.12 environment |
| Extracted-source install smoke | PASS | Built source distribution |
| Dependency lock | PASS | Deterministic lock validation |
| Vulnerability exceptions | PASS | Policy validation |
| PyPI advisory audit | PASS | No known vulnerabilities |
| OSV advisory audit | PASS | No known vulnerabilities |
| Current deterministic SBOM | PASS | CycloneDX 1.5; locked runtime graph |
| Benchmark corpus execution | PASS as pipeline smoke test | 60 deterministic generated judgments |
| Independent governed diff review | NOT RUN | Awaiting Ryan's approval checkpoint |

The Release Validation Workbench passed every executable gate it ran and reported
`blocked` solely because independent governed review was not supplied. That is the
correct result at this checkpoint.

## Calibration integrity finding

The generated benchmark achieved 100% label accuracy and macro F1, but it is not
independent intelligence-quality evidence. The benchmark compiler maps each domain
to a fixed governed label; therefore generated labels can validate deterministic
pipeline execution but cannot establish case-level reasoning accuracy.

The current generated calibration report is correctly not release eligible:

- Brier score: 0.2347099697 (above policy).
- Expected calibration error: 0.48446875 (above policy).
- Expert reviewer acceptance: missing for all 60 cases.
- All eight domain calibration-error gates failed.

The default calibration policy now blocks release eligibility when any case lacks
explicit expert reviewer acceptance or is rejected. Confidence was not inflated to
make the generated data pass.

## Candidate decision

The governed decision-pipeline implementation is internally consistent and passes
the repository's software-quality, packaging, dependency, and security gates.
Candidate designation remains blocked pending:

1. Ryan's review of this diff and authorization to commit/push.
2. Case-level expert review and acceptance of benchmark judgments, or replacement
   with an independently labeled evaluation corpus.
3. A final governed release review after source freeze.

Production promotion remains a separate transaction requiring explicit approval
and live authority readback. No production authority was changed.
