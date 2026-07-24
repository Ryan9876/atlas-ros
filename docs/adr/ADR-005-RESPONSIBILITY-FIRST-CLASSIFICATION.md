# ADR-005 — Responsibility-First Classification Intelligence

- Status: Accepted for development
- Date: 2026-07-24
- Program: ATI-1 / IDEA-1 / IDEA-2 / IDEA-3
- Production impact: None until separately authorized promotion

## Context

Atlas ROS v5.2.0 separates the provider-independent Management Reasoning Engine from deterministic record routing, but the engine still receives a pre-existing routing recommendation. It does not independently determine why Ryan owns an outcome, cannot represent responsibility domain or operating context, and only restates classification and destination as its explanation.

Activity-first classification can misroute managerial work. A technical action performed to enable a direct report may be classified as Operations even though the primary responsibility is People Leadership. Similar ambiguity exists between project delivery, operational stewardship, external dependencies, and capability building.

## Decision

The Management Reasoning Engine will own classification intelligence using this ordered model:

`Responsibility -> Outcome -> Workstream -> Activity`

Record classification and provider destination remain separate dimensions. The Record Routing Service remains the deterministic authority for validating classification-to-destination mappings. Provider adapters cannot classify work or authorize provider writes.

The version 2 reasoning contract adds:

- responsibility domain;
- desired outcome;
- management workstream;
- activity summary;
- operating context and independent context confidence;
- decisive evidence signals;
- concise user-facing rationale;
- ambiguity, challenge, and fallback state;
- explicit version 1 compatibility projection.

The initial responsibility taxonomy is:

1. People Leadership -> Leadership & Team
2. Project Delivery -> Active Projects
3. Operational Stewardship -> Operations
4. External Dependency -> Waiting on Others
5. Capability Building -> Development & Learning

Manager intent is supporting evidence only. It cannot override stronger explicit responsibility, ownership, authority, safety, project, decision, or risk evidence.

## Rollout

1. Shadow mode computes semantic reasoning without changing routing authority.
2. Attended mode exposes semantic decisions and explanations while preserving legacy authority.
3. Explicit semantic mode is available for validated development and acceptance testing.
4. Production activation requires a governed compatibility candidate, Full Validation, rollback proof, and Ryan's explicit promotion decision.

The default W02 mode remains legacy. This ADR does not activate production behavior.

## Quality gates

- Critical responsibility and authority fixtures: 100%.
- Responsibility-domain macro F1: at least 0.90.
- Recall per responsibility domain: at least 0.85.
- Non-target record classification and destination equivalence: at least 0.99.
- Confidence calibration error: no greater than 0.10.
- Explanation-to-evidence agreement: at least 0.95.
- Existing v5.2 regression, packaging, security, restoration, and rollback gates remain blocking.

## Consequences

### Positive

- Classification reflects managerial accountability rather than technical vocabulary alone.
- Decisions become explainable, challengeable, and auditable.
- Provider boundaries and deterministic routing remain intact.
- Version 1 consumers remain compatible.

### Costs and risks

- Governed taxonomies and evaluation datasets require maintenance.
- Confidence can be wrong or poorly calibrated; low-confidence cases must fail safely.
- Deterministic patterns may miss novel phrasing; shadow evidence and challenge records provide tuning inputs.
- The semantic capability must not be confused with permission to activate production behavior.
