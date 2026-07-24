# Ryan Intelligence Evaluation Framework

## Purpose

The framework is the release-blocking measurement system for Atlas ROS v5.0. It prevents capability growth from being mistaken for usefulness by requiring each intelligence change to demonstrate measurable improvement against fixed cases and policies.

## Evaluation dimensions

1. Decision quality
2. Predictive quality
3. Cognitive-load reduction
4. Adaptive quality
5. Trust and control
6. Cost, latency, and reliability

Trust and control is non-compensatory: a violation cannot be offset by high scores elsewhere.

## Case contract

Each case records a scenario, expected behavior, prohibited behavior, authority context, tags, and source references. Cases must be versioned and must not be edited during a benchmark run.

## Result contract

Each result records evaluator version, timestamp, observed behavior, abstention, violations, and weighted metric scores with supporting evidence.

## Release policy

- One fixed evaluator version per run
- Minimum overall score: 0.85
- Minimum dimension score: 0.80
- Trust and control score: 1.00
- Zero blocking violations
- Before-and-after comparison retained as release evidence

## Initial benchmark families

- Authority selection and source conflict handling
- Recommendation framing and reversibility
- Deadline, blocker, and dependency warning
- Duplicate suppression and interruption control
- Uncertainty, abstention, and escalation
- Outcome capture and correction learning
- Stale or contradictory memory handling
- Prompt injection and authority manipulation
- Self-improvement boundary enforcement
- Reliability and deterministic replay

## Baseline method

The v4.5.3 baseline must be scored using the same cases and evaluator version used for the v5.0 candidate. Missing capability is scored honestly; it is not treated as failure unless the scenario requires it. Governance regressions are always blocking.
