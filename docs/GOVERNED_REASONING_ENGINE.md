# Governed Reasoning and Recommendation Engine

Milestone 5 adds deterministic, evidence-first decision support over Canonical Intelligence Records.

## Guarantees

- Context and evidence references are resolved through the append-only record store.
- Rejected or below-threshold evidence cannot support a recommendation.
- Every alternative is scored against the same complete criterion set.
- Criteria support maximize and minimize direction with normalized weighted utility.
- Evidence strength combines source authority and confidence.
- Adjusted option scores combine utility and evidence strength.
- The engine abstains when no usable evidence exists or the leading margin is below policy.
- Successful evaluations produce an immutable RecommendationRecord and an explainable ReasoningTrace.
- No external action, production authority change, or autonomous execution occurs.

## Decision quality

The engine exposes a bounded decision-quality score derived from adjusted option quality, uncertainty, and explanation completeness. This is an engineering evaluation signal, not a claim of measured real-world decision performance.
