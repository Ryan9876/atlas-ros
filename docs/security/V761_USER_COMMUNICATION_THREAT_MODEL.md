# Atlas ROS v7.6.1 User Communication Threat Model

## Protected assets

Ryan identity binding, workspace binding, minimized preferences, governed evidence provenance, profile digest, feature state, current-instruction precedence, provider boundaries, and release authority.

## Threats and controls

| Threat | Control |
|---|---|
| Sensitive profile leakage | No production profile in package, fixtures, PR text, release notes, or raw traces; redacted inspection only |
| Prompt injection in assessment files | Treat all assessment text as untrusted data; embedded instructions are never authorized |
| Profile treated as authorization | Typed zero-effect fields; current instruction and live authority precedence; provider-write tests |
| Stale, expired, rejected, or superseded preference | Review/expiry/confirmation/override checks and safe fallback |
| Incorrect identity or cross-user contamination | Exact user, workspace, repository, context, and version binding; fail closed |
| Malicious profile modification | Deterministic digest, immutable candidate identity, access control, readback, and disable procedure |
| Contradictory assessments collapsed into identity | Preserve contradiction state and context-specific interpretations; exclude open contradictions |
| Inferred protected or clinical characteristics | Prohibited learning source and minimization scan |
| Excessive context injection | Bounded compiler output and compact directives only |
| Clarification bypass | Consequential flag and preserved v7.5 clarification decision |
| Telemetry disclosure | Raw profile absent; reason codes and hashed preference identities only |
| Provider side effects | Literal zero-write contract fields, regression tests, and zero-write receipt |

## Failure behavior

Any missing, invalid, corrupted, expired, cross-boundary, contradicted, or unauthorized profile state falls back to Atlas ROS v7.6.0 behavior. It does not partially adapt and does not write to providers.
