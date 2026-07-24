# Atlas ROS v5.0.0rc1 Current Candidate Validation Report

Validation window: 2026-07-22 America/Detroit / 2026-07-23 UTC

Status: **Implementation and quantitative calibration validated; not yet a release Candidate.**

This report covers the uploaded authoritative working copy on
`atlas/release-v500-candidate`, including the local calibration correction after
published commit `ec074198123a42fc7d62226d46da96dd1cc268c0`. It does not
authorize a commit, push, Candidate declaration, or production promotion. Atlas
ROS v4.5.3 remains Active and v4.5.2 remains the immediate immutable rollback.

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
| Full regression suite | PASS | 242 tests |
| Branch coverage | PASS | 89.10%, threshold 85% |
| Source and wheel build | PASS | `atlas-ros==5.0.0rc1` |
| Clean-wheel install and calibration-policy smoke | PASS | Fresh Python 3.12 environment |
| Extracted-source install smoke | PASS | Built source distribution |
| Dependency lock | PASS | Deterministic lock validation |
| Vulnerability exceptions | PASS | Policy validation |
| PyPI advisory audit | PASS | No known vulnerabilities |
| OSV advisory audit | PASS | No known vulnerabilities |
| Current deterministic SBOM | PASS | CycloneDX 1.5; locked runtime graph |
| Benchmark corpus execution | PASS | 60 deterministic generated judgments; all quantitative gates pass |
| Reproducible build | PASS | Byte-identical source and wheel pairs |
| Governed release review | NOT RUN | Solo-maintainer review required after source freeze |

The Release Validation Workbench passed every executable gate it ran. Governed
review remains a manual blocking gate and may be satisfied through Ryan's
documented solo-maintainer review after source freeze.

## Calibration correction and integrity boundary

The generated benchmark achieved 100% label accuracy and macro F1, but it is not
independent intelligence-quality evidence. The benchmark compiler maps each domain
to a fixed governed label; therefore generated labels can validate deterministic
pipeline execution and confidence behavior but cannot establish independent,
real-world case-level reasoning accuracy.

The calibration defect was a semantic mismatch. The judgment mapper treated
`RecommendationRecord.confidence`, an absolute action-safety score that includes
evidence, claim, graph-support, and decision-margin penalties, as the probability
that the selected benchmark label was correct. Calibration now uses the leading
option's share of all non-negative adjusted option scores. The recommendation's
conservative action-safety confidence is unchanged.

Current 60-case result:

- Accuracy: 1.0.
- Macro F1: 1.0.
- Brier score: 0.0061446002 (required <=0.16).
- Expected calibration error: 0.0783875 (required <=0.10).
- Hallucination rate: 0.0.
- All eight domain accuracy and calibration gates pass.
- Blocking violations: none.

Ryan waived case-level expert acceptance as a release-blocking gate for v5.0.
Reviewer acceptance remains recorded as advisory evidence. The waiver does not
alter any quantitative threshold. The correction changes which existing
confidence semantic is supplied to the probability-calibration metrics; it does
not raise recommendation confidence or lower a gate. The authority for the
acceptance waiver is Decision Log record
[`V4D-12`](https://app.notion.com/p/3a6b8344ad2c81cba4a7fc8c951b6335).

## Candidate decision

The governed decision-pipeline implementation is internally consistent and
passes the repository's software-quality, quantitative calibration, packaging,
dependency, and security gates. The final Release Validation Workbench run
passes every executable gate and remains blocked only because governed review
evidence has not yet been supplied.

Candidate designation remains pending:

1. Ryan's authorization to commit and push the calibration correction.
2. GitHub CI validation of the published calibration-fix commit.
3. A final solo-maintainer governed release review bound to the exact frozen
   commit and artifact checksums.
4. Refreshed promotion and restoration evidence against that exact release state.

Production promotion remains a separate transaction requiring explicit approval
and live authority readback. No production authority was changed.
