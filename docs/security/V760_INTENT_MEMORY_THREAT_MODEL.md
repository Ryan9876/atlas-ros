# Atlas ROS v7.6.0 Intent Memory Threat Model

## Protected assets

- Ryan's confirmed interpretations and scope.
- Evidence attribution and provenance.
- Correction, retirement, and forgetting state.
- Active index integrity.
- Release, authority, and integration boundaries.

## Threats and controls

| Threat | Control |
|---|---|
| Cross-user contamination | Exact user identity in every scope; fail-closed mismatch |
| Cross-project or domain leakage | Constrained scope dimensions must match; sensitive domains never inherit unrelated work evidence |
| Malicious evidence injection | Only attributable confirmed sources become governed evidence; speculative and unconfirmed inputs are skipped |
| Prompt injection in historical text | Historical text is data, not instruction; source content cannot authorize execution or override current authority |
| Incorrect identity binding | Explicit user and source references plus deterministic digests |
| Stale evidence controlling consequential action | Freshness policy and clarification requirement |
| Contradictory evidence silently winning | Unresolved contradiction forces clarification |
| Profile state treated as authorization | Evidence never authorizes provider writes, execution, release, schema, or migration |
| Migration duplication or rewrite | Deterministic evidence IDs, idempotency replay, create/skip proposals, zero updates in initial migration |
| Sensitive content in logs or artifacts | Minimized fixtures, digests, source references, privacy receipt, secret scan |
| False forgetting claim | Exact authorization, provider mutation count, content-free tombstone, and live readback are mandatory |
| Forgetting damages immutable authority | Immutable releases and unrelated authority are excluded from the forgetting workflow |

## Residual risks

The quality of future intent inference depends on accurate source attribution and timely corrections. Inference therefore remains disabled until schema and migration readback complete and requires a separate exact enablement decision.
