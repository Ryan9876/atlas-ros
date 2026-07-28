# Atlas ROS v7.1 Candidate Threat Model

## Protected assets

Release authority, immutable package identity, rollback assets, retention evidence, exact cleanup inventories, authorization, provider state, credentials, and canonical plans.

## Threats and controls

| Threat | Control |
|---|---|
| Drive silently reintroduced as authority or runtime dependency | Repository inventory, architecture rules, required-integration exact set, disconnected-Drive tests |
| Historical evidence deleted through broad folder authorization | Item-level digest-bound inventory, exact item IDs, retention classification, blockers, object and byte budgets |
| Unknown or conflicting retention classification | Fail closed as human-decision required |
| Cleanup applied to changed object | Expected digest check and uncertain-apply readback |
| Duplicate destructive operation | Deterministic idempotency key and provider readback |
| Partial cleanup hidden as success | Item-level result/readback sets and partial/failed receipt status |
| Candidate workflow claims production | Candidate-only contracts and false/zero publication, activation, authority and provider-write fields |
| Release script drift | Single compiler and compatibility wrappers without independent policy |
| Production imports migration or release code | Architecture and import-boundary validators |
| Lazy loading changes policy by import order | Immutable command registry and deterministic equivalence tests |
| Warm cache becomes authority | Authentication, TTL, source digest, non-authoritative marker, allowed-kind list, provider writes zero |
| Cached authorization or mutable provider truth | Type-level allowed snapshot kinds and negative tests |
| Credential or connector retirement without scope | Separate exact transaction contract; no live retirement adapter enabled |

## Residual risks

A future provider adapter must prove connector-specific idempotency and readback semantics. Legal, audit, security, and governance retention decisions remain human-controlled. Warm runtime remains optional and must be disabled if freshness cannot be established.
