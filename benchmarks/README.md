# Ryan Intelligence Evaluation Set v1

## Execution Planning and Task Economy

`execution-planning-v1.json` is the release-blocking v5.5 benchmark. It contains
52 deterministic cases spanning ownership, readiness, binary completion,
duplicate and existing-representation suppression, progressive horizons,
task-budget thresholds, anti-bloat invariance, multiple parent outcomes,
provider separation, compatibility, and authorization boundaries.

Run:

```bash
python scripts/evaluate_execution_planning.py \
  --dataset benchmarks/execution-planning-v1.json \
  --output execution-planning-evidence/EXECUTION_PLANNING_REPORT.json
```

Promotion requires every case and every critical fixture to pass, with zero
provider writes and zero authorized execution objects.

Versioned promotion benchmark for Atlas ROS v5.0. The corpus contains 60 provisional gold cases across eight intelligence domains and six operating contexts. Cases marked `critical` or `adversarial` are release blocking. Case-level expert acceptance is advisory under the v5.0 policy waiver; quantitative benchmark thresholds and the final solo-maintainer governed release review remain blocking.

Calibration confidence represents the governed label's relative share of the
adjusted option scores. It is separate from the recommendation record's absolute
action-safety confidence. The generated corpus remains deterministic pipeline
and calibration evidence rather than an independently labeled measure of
real-world reasoning accuracy.

## Semantic Fidelity and Test-Instruction Invariance

`semantic-fidelity-v1.json` is the release-blocking v6.1 benchmark. It contains
expert-approved golden outputs, seven CloudVision metamorphic variants, audit-primary
negative controls, reusable controlled-pilot cases, and fail-closed ambiguity cases.

Run:

```bash
python scripts/evaluate_semantic_fidelity.py \
  --dataset benchmarks/semantic-fidelity-v1.json \
  --output semantic-fidelity-evidence/SEMANTIC_FIDELITY_REPORT.json
```

Promotion requires every critical case and every metamorphic family to pass with zero
live provider writes. Structural compatibility remains necessary but is not a substitute
for expert semantic gold.
