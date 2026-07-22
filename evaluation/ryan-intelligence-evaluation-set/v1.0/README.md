# Ryan Intelligence Evaluation Set v1.0

This corpus is the fixed initial benchmark for Atlas ROS v5.0 core development.

## Purpose

Measure whether future changes improve practical decision support, prediction, cognitive-load reduction, adaptation, trust and control, and operational reliability without moving the benchmark after results are known.

## Baseline interpretation

`baseline-v4.5.3.json` is a **documented capability baseline**. It records what v4.5.3 demonstrably implements or governs from release evidence. It is not a live transcript replay and must not be described as measured production effectiveness.

Future behavioral baselines must use preserved prompts, source snapshots, outputs, evaluator version, and timestamps. Documented-capability and behavioral-observation results must remain separately labeled.

## Governance

- Case IDs and expected/prohibited behaviors are immutable within v1.0.
- Corrections require a new evaluation-set version and change rationale.
- Trust-and-control violations are release blocking.
- Evaluator policy cannot be modified during a benchmark run.
- No benchmark result can directly promote or modify production.
